
import random
from api import logger
from core.models import db, User, Event, Experiment


class ExperimentDAO:
    def __init__(self, current_user: User, experiment_name, choices: list[str], experiment: Experiment = None):
        """
        Create a new instance of an experiment by naming it and listing off the possible choices.
        If the name is new or the choices have changed, a new Experiment record is created and referenced.
        :param current_user:
        :type current_user:
        :param experiment_name:
        :type experiment_name:
        :param choices:
        :type choices:
        :param experiment:
        :type experiment:
        """
        self.user = current_user
        self.name = experiment_name
        if experiment is None:
            self.experiment = self.get_or_update_experiment(experiment_name=self.name, choices=choices)
        else:
            self.experiment = experiment

    @staticmethod
    def get_or_update_experiment(experiment_name, choices: list[str]) -> Experiment:
        """
        Get an experiment by name. If the choices have changed, create a new experiment record.
        :param experiment_name:
        :type experiment_name:
        :param choices:
        :type choices:
        :return:
        :rtype:
        """
        exp = Experiment.get_by_name(experiment_name)
        if exp is None:
            exp = Experiment.create_new(experiment_name=experiment_name, choices=choices)
        elif exp.choices_list_is_updated(choices):
            # Create a new record if the choices have been updated
            exp = Experiment.create_new(experiment_name=experiment_name, choices=choices)
        return exp

    @staticmethod
    def get_optimal_choice(choice_records: dict):
        """
        Get the best choice from a dict of {choice_name: {'pulls': 0, 'rewards': 0}, ...} using thompson sampling
        :param choice_records:
        :type choice_records:
        :return:
        :rtype:
        """
        sampled_theta = {}
        for key, choice in choice_records.items():
            # Draw from beta distribution of beta( prior[0] + trials, prior[1] + failures )
            pulls, rewards = float(choice['pulls']), float(choice['rewards'])
            dist = random.betavariate(1.0 + rewards, 1.0 + pulls - rewards)
            sampled_theta[key] = dist
        return max(sampled_theta, key=sampled_theta.get)

    def pull(self, subset_key=None):
        """
        Check if the user has a history with this experiment.
        If not, use Thompson Sampling to pick the optimal choice from a list of choice keys.
        :return:
        :rtype:
        """
        prev_event = Event.get_by_user_and_experiment(self.user, self.name)
        if prev_event is None:
            choice_records = Event.get_scores(experiment_name=self.name,
                                              choices=self.experiment.choices,
                                              subset_key=subset_key)
            out_name = self.get_optimal_choice(choice_records=choice_records)
            Event.create_new(user_id=self.user.id, name=self.name, choice_key=out_name, subset_key=subset_key)
            return out_name
        else:
            return prev_event.choice_key

    def reward(self):
        """
        Apply a reward signal to an experiment choice, making that choice more likely in the future.
        :return:
        :rtype:
        """
        prev_event = Event.get_by_user_and_experiment(self.user, self.name)
        if prev_event is None:
            logger.warning(f'could not find Event to reward for user={self.user.id} and experiment={self.name}')
            return None
        elif prev_event.reward_event is False:
            prev_event.reward_event = True
            db.session.commit()
            return prev_event
        else:
            return prev_event

    def safe_pull(self, subset_key=None):
        """ Pull on the MAB, but suppress any errors that may occur. """
        try:
            return self.pull(subset_key=subset_key)
        except Exception as err:
            logger.warning(f"exception swallowed in ExperimentDAO.pull - {err}")
            return None

    def safe_reward(self):
        """ Reward the MAB, but suppress any errors that may occur. """
        try:
            return self.reward()
        except Exception as err:
            logger.warning(f"exception swallowed in ExperimentDAO.reward - {err}")
            return None

