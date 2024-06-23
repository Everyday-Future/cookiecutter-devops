"""

Locust is used for load testing services with fake users.
We configure different behaviors for users and then flood the server with an increasing number of these
artificial users to look at the performance impact of different behaviors.

"""

import time
import random
from locust import HttpUser, task, between
from config import Config
from fixtures import BrowserController, get_webdriver


class QuickstartUser(HttpUser):
    wait_time = between(2.5, 10)
    driver = None

    def on_start(self):
        self.driver = get_webdriver()
        time.sleep(0.5)
        self.driver.get(Config.SERVER_URL)
        time.sleep(0.5)

    @task(10)
    def homepage_bounce(self):
        """
        User customizes a book and gets the pdf printable
        """
        env = BrowserController(driver=self.driver, server_url=Config.SERVER_URL)
        self.driver.get(env.server_url + "/index")
        time.sleep(random.random())
        env.scroll_to(2000)
        time.sleep(random.random())
