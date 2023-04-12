import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


class SendgridSender:
    """
    Email queue to to added to by the website backend and cleared by the renderer worker.
    """
    @staticmethod
    def send(subject, txt_content, html_content, to_list, from_email, send_at):
        """
        Send an email in the current thread or in a new, separate thread.

        subject=email_template.subject,
                         txt_content=email_template.txt_content,
                         html_content=email_template.html_content,
                         to_list=to_list,
                         from_email=self.from_email

        :param subject: Subject line for the email
        :param from_email: "From" address for the email.
        :param to_list: Email recipient(s). String or list of strings.
        :param txt_content: Path to the txt template to use for the email.
        :param html_content: Path to the html template to use for the email.
        :param send_at: Epoch time to schedule the email send for
        :return:
        """
        message = Mail(
            from_email=from_email,
            to_emails=to_list,
            subject=subject,
            html_content=html_content,
            plain_text_content=txt_content)
        message.send_at = send_at
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        assert response.status_code == 202
        return True
