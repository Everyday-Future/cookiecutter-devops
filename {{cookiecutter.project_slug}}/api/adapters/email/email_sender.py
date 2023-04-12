"""

Abstract Email client

Send emails and (if the option is available) schedule send for later

"""

import os
import json
import time
from itsdangerous import URLSafeSerializer
from api import global_config, logger
from api.models import User
from api.daos.renderer_base import edit_string
from api.adapters.storage.storage import Storage
from api.adapters.email.email_sender_sendgrid import SendgridSender


class EmailTemplate:
    """
    All of the content needed to compile and render an email
    """

    def __init__(self, name: str, description: str, subject: str, txt_content: str, html_content: str,
                 txt_fname: str, html_fname: str, params: dict):
        """
        Compile an email template into it's final state before sending
        :param name: unique name for the email template
        :type name: str
        :param description: description of the purpose of the template
        :type description: str
        :param subject: email subject with jinja2-injectable params
        :type subject: str
        :param txt_content: text content or path to text content for the email with jinja2-injectable params
        :type txt_content: str
        :param html_content: html content or path to html content for the email with jinja2-injectable params
        :type html_content: str
        :param txt_fname: text content or path to text content for the email with jinja2-injectable params
        :type txt_fname: str
        :param html_fname: html content or path to html content for the email with jinja2-injectable params
        :type html_fname: str
        :param params: Parameters to be injected with jinja2
        :type params: dict
        """
        self.name = name
        self.description = description
        self.params = params
        # Inject variables in the subject if needed
        self.subject = edit_string(subject, self.params)
        # Open the txt content if it's a filename instead of raw content
        if os.path.exists(txt_fname) and os.path.isfile(txt_fname):
            with open(txt_fname, 'r') as fp:
                txt_content = fp.read()
        self.txt_content = edit_string(txt_content, self.params)
        # Open the html content if it's a filename instead of raw content
        if os.path.exists(html_fname) and os.path.isfile(html_fname):
            with open(html_fname, 'r') as fp:
                html_content = fp.read()
        self.html_content = edit_string(html_content, self.params)
        self.sent = False

    def save(self, to_email, target_dir=None, storage: Storage = None):
        """
        Save a copy of the html or txt body of the email
        :param to_email:
        :param target_dir:
        :param storage:
        :return:
        """
        # Save to the screenshots dir if not specified
        if target_dir is None:
            target_dir = global_config.SCREENSHOT_DIR
        if not os.path.isdir(target_dir):
            os.makedirs(target_dir, exist_ok=True)
        # Save the compiled TXT and HTML email bodies
        with open(os.path.join(target_dir, f'{self.name}_{to_email}.txt'), 'w', encoding='utf8') as fp:
            fp.write(self.txt_content)
        with open(os.path.join(target_dir, f'{self.name}_{to_email}.html'), 'w', encoding='utf8') as fp:
            fp.write(self.html_content)
        # Upload to cloud storage if specified
        if isinstance(storage, Storage):
            storage.upload(f'{self.name}_{to_email}.txt', os.path.join(target_dir, f'{self.name}_{to_email}.txt'))
            storage.upload(f'{self.name}_{to_email}.html', os.path.join(target_dir, f'{self.name}_{to_email}.html'))

    def mark_sent(self, to_list: list, storage: Storage = None):
        """
        Mark an email as having been sent. Log and save diagnostic data
        :param to_list:
        :type to_list:
        :param storage:
        :type storage:
        :return:
        :rtype:
        """
        self.sent = True
        for to_email in to_list:
            if isinstance(to_email, User):
                to_email = to_email.email
            logger.info({'message': f'New {self.name} email sent to {to_email}'})
            self.save(to_email=to_email, storage=storage)


class EmailSender:
    """
    Send an email
    """

    def __init__(self, sender_type='sendgrid', from_email=None, send_at: int = None, storage: Storage = None):
        self.from_email = from_email or global_config.ADMINS[0]
        self.send_at = int(send_at or time.time())
        self.storage = storage
        if sender_type == 'sendgrid':
            self.sender = SendgridSender()
        else:
            raise ValueError(f"email_sender - Unrecognized sender_type of {sender_type}")

    def get_params(self, target_user: User = None, params: dict = None,
                   cta_link=None, cta_msg='Check It Out', add_unsub=True, add_invite=False):
        """
        Get a dict of params to update an email template with
        :param target_user:
        :type target_user:
        :param params:
        :type params:
        :param cta_link:
        :type cta_link:
        :param cta_msg:
        :type cta_msg:
        :param add_unsub:
        :type add_unsub:
        :param add_invite:
        :type add_invite:
        :return:
        :rtype:
        """
        unsub_url = ''
        if target_user is not None:
            unsub_url = self.get_unsub_url(target_user.email)
        base_dict = dict(backend_url=global_config.SERVER_URL, user_hash=target_user.token,
                         add_cta=cta_link is not None, add_unsub=add_unsub, add_invite=add_invite,
                         unsub_url=unsub_url, name='', section=[], main_img_url='',
                         main_header='', main_subheading='', btn_txt=cta_msg, btn_url=cta_link)
        if params is not None:
            base_dict.update(params)
        return base_dict

    def send_email_template(self, email_template: EmailTemplate, to_list: list):
        """
        Send an email intended to be a direct update to a user, like shipment notifications
        :param email_template:
        :type email_template: EmailTemplate
        :param to_list: List of User models or email strings
        :type to_list: list
        :return:
        :rtype:
        """
        # Check that the email hasn't already been sent
        if email_template.sent is False:
            is_sent = self.sender.send(subject=email_template.subject,
                                       txt_content=email_template.txt_content,
                                       html_content=email_template.html_content,
                                       to_list=to_list,
                                       from_email=self.from_email,
                                       send_at=self.send_at)
            # If no error was raised by the sender, mark the email sent and save the record in storage
            if is_sent is True:
                email_template.mark_sent(to_list=to_list, storage=self.storage)


class EmailTemplatesDAO:
    with open(os.path.join(global_config.TEXT_DIR, 'emails.json'), 'r') as fp:
        _templates = json.load(fp)
        for template_name, template in _templates.items():
            if (template.get('html_fname') or '') != '':
                template['html_fname'] = os.path.join(global_config.EMAIL_TEMPLATES_DIR, template['html_fname'])
            if (template.get('txt_fname') or '') != '':
                template['txt_fname'] = os.path.join(global_config.EMAIL_TEMPLATES_DIR, template['txt_fname'])

    @classmethod
    def get_markdown(cls, template_name):
        """
        Get the raw markdown for an email template by name
        :param template_name:
        :type template_name:
        :return:
        :rtype:
        """
        return cls._templates[template_name]

    @classmethod
    def get(cls, template_name, email_params: dict):
        """
        Get the fully-compiled markdown for an email template by name
        :param template_name: The name of the email template to load
        :type template_name: str
        :param email_params: The params to be used to populate the template
        :type email_params: dict
        :return:
        :rtype:
        """
        template_md = cls.get_markdown(template_name=template_name)
        template_md['name'] = template_name
        template_md['params'] = email_params
        return EmailTemplate(**template_md)
