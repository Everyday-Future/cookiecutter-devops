"""

Reddit API

https://praw.readthedocs.io/en/stable/index.html

"""
import praw
from config import Config


class RedditAPI:
    client_id = Config.REDDIT_CLIENT_ID
    client_secret = Config.REDDIT_CLIENT_SECRET
    user_agent = Config.REDDIT_USER_AGENT

    @classmethod
    def search_subreddit(cls, subreddit_name='python'):
        # Initialize PRAW with your credentials
        reddit = praw.Reddit(
            client_id=cls.client_id,
            client_secret=cls.client_secret,
            user_agent=cls.user_agent
        )
        # Access the subreddit
        subreddit = reddit.subreddit(subreddit_name)
        # Fetch the latest 10 posts
        for submission in subreddit.new(limit=100):
            print(f"Title: {submission.title}, Upvotes: {submission.score}")
            # Fetch and print top comment, if it exists
            submission.comment_sort = 'best'
            submission.comments.replace_more(limit=0)  # Load all comments
            top_comments = list(submission.comments)
            print("top_comments", top_comments)
            # if top_comments:
            #     top_comment = top_comments[0]
            #     print(f"Top comment: {top_comment.body}\n")
            # else:
            #     print("No comments yet.\n")
            return top_comments[0].body

    @classmethod
    def top_subreddit(cls, subreddit_name='python'):
        """
        time_filter: Can be one of: ``"all"``, ``"day"``, ``"hour"``,
            ``"month"``, ``"week"``, or ``"year"`` (default: ``"all"``).
        :param subreddit_name:
        :return:
        """
        # Initialize PRAW with your credentials
        reddit = praw.Reddit(
            client_id=cls.client_id,
            client_secret=cls.client_secret,
            user_agent=cls.user_agent
        )
        # Access the subreddit
        subreddit = reddit.subreddit(subreddit_name)
        # Prepare a list to store posts and their top comments
        posts = []
        # Fetch the latest 10 posts
        for submission in subreddit.new(limit=10):
            post_info = {
                "title": submission.title,
                "upvotes": submission.score,
                "top_comment": ""
            }
            # Fetch and assign top comment, if it exists
            submission.comment_sort = 'best'
            submission.comments.replace_more(limit=0)  # Load all comments
            top_comments = list(submission.comments)
            if top_comments:
                post_info["top_comment"] = top_comments[0].body
            posts.append(post_info)
        return posts


class YouTubeAPI:
    """
    Scan across YouTube channels and download transcripts and descriptions.
    Each video is an Article and the YouTube channel is the Publisher which has youtube- pre-pended to its name
    In the future, we can download and process the video.
    """

    def parse_video(self, video_url):
        """
        Gather data from a video, including its description and transcript.
        """

    def crawl_channel(self, channel_name):
        pass
