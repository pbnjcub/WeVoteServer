# analytics/models.py
# Brought to you by We Vote. Be good.
# -*- coding: UTF-8 -*-

from django.db import models
from django.db.models import Q
from django.utils.timezone import localtime, now
from datetime import datetime, timedelta
from election.models import Election
from exception.models import print_to_log
from follow.models import FollowOrganizationList
from organization.models import Organization
import pytz
import wevote_functions.admin
from wevote_functions.functions import convert_to_int, positive_value_exists
from wevote_functions.functions_date import convert_date_as_integer_to_date, convert_date_to_date_as_integer, generate_localized_datetime_as_integer
from wevote_settings.models import WeVoteSetting, WeVoteSettingsManager

ACTION_VOTER_GUIDE_VISIT = 1
ACTION_VOTER_GUIDE_ENTRY = 2  # DEPRECATED: Now we use ACTION_VOTER_GUIDE_VISIT + first_visit
ACTION_ORGANIZATION_FOLLOW = 3
ACTION_ORGANIZATION_AUTO_FOLLOW = 4
ACTION_ISSUE_FOLLOW = 5
ACTION_BALLOT_VISIT = 6
ACTION_POSITION_TAKEN = 7
ACTION_VOTER_TWITTER_AUTH = 8
ACTION_VOTER_FACEBOOK_AUTH = 9
ACTION_WELCOME_ENTRY = 10
ACTION_FRIEND_ENTRY = 11
ACTION_WELCOME_VISIT = 12
ACTION_ORGANIZATION_FOLLOW_IGNORE = 13
ACTION_ORGANIZATION_STOP_FOLLOWING = 14
ACTION_ISSUE_FOLLOW_IGNORE = 15
ACTION_ISSUE_STOP_FOLLOWING = 16
ACTION_MODAL_ISSUES = 17
ACTION_MODAL_ORGANIZATIONS = 18
ACTION_MODAL_POSITIONS = 19
ACTION_MODAL_FRIENDS = 20
ACTION_MODAL_SHARE = 21
ACTION_MODAL_VOTE = 22
ACTION_NETWORK = 23
ACTION_FACEBOOK_INVITABLE_FRIENDS = 24
ACTION_DONATE_VISIT = 25
ACTION_ACCOUNT_PAGE = 26
ACTION_INVITE_BY_EMAIL = 27
ACTION_ABOUT_GETTING_STARTED = 28
ACTION_ABOUT_VISION = 29
ACTION_ABOUT_ORGANIZATION = 30
ACTION_ABOUT_TEAM = 31
ACTION_ABOUT_MOBILE = 32
ACTION_OFFICE = 33
ACTION_CANDIDATE = 34
ACTION_VOTER_GUIDE_GET_STARTED = 35
ACTION_FACEBOOK_AUTHENTICATION_EXISTS = 36
ACTION_GOOGLE_AUTHENTICATION_EXISTS = 37
ACTION_TWITTER_AUTHENTICATION_EXISTS = 38
ACTION_EMAIL_AUTHENTICATION_EXISTS = 39
ACTION_ELECTIONS = 40
ACTION_ORGANIZATION_STOP_IGNORING = 41
ACTION_MODAL_VOTER_PLAN = 42
ACTION_READY_VISIT = 43
ACTION_SELECT_BALLOT_MODAL = 44
ACTION_SHARE_BUTTON_COPY = 45
ACTION_SHARE_BUTTON_EMAIL = 46
ACTION_SHARE_BUTTON_FACEBOOK = 47
ACTION_SHARE_BUTTON_FRIENDS = 48
ACTION_SHARE_BUTTON_TWITTER = 49
ACTION_SHARE_BALLOT = 50
ACTION_SHARE_BALLOT_ALL_OPINIONS = 51
ACTION_SHARE_CANDIDATE = 52
ACTION_SHARE_CANDIDATE_ALL_OPINIONS = 53
ACTION_SHARE_MEASURE = 54
ACTION_SHARE_MEASURE_ALL_OPINIONS = 55
ACTION_SHARE_OFFICE = 56
ACTION_SHARE_OFFICE_ALL_OPINIONS = 57
ACTION_SHARE_READY = 58
ACTION_SHARE_READY_ALL_OPINIONS = 59
ACTION_VIEW_SHARED_BALLOT = 60
ACTION_VIEW_SHARED_BALLOT_ALL_OPINIONS = 61
ACTION_VIEW_SHARED_CANDIDATE = 62
ACTION_VIEW_SHARED_CANDIDATE_ALL_OPINIONS = 63
ACTION_VIEW_SHARED_MEASURE = 64
ACTION_VIEW_SHARED_MEASURE_ALL_OPINIONS = 65
ACTION_VIEW_SHARED_OFFICE = 66
ACTION_VIEW_SHARED_OFFICE_ALL_OPINIONS = 67
ACTION_VIEW_SHARED_READY = 68
ACTION_VIEW_SHARED_READY_ALL_OPINIONS = 69
ACTION_SEARCH_OPINIONS = 70
ACTION_UNSUBSCRIBE_EMAIL_PAGE = 71
ACTION_UNSUBSCRIBE_SMS_PAGE = 72
ACTION_MEASURE = 73
ACTION_NEWS = 74
ACTION_SHARE_ORGANIZATION = 75
ACTION_SHARE_ORGANIZATION_ALL_OPINIONS = 76
ACTION_VIEW_SHARED_ORGANIZATION = 77
ACTION_VIEW_SHARED_ORGANIZATION_ALL_OPINIONS = 77

ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS = \
    [ACTION_ORGANIZATION_AUTO_FOLLOW,
     ACTION_ORGANIZATION_FOLLOW, ACTION_ORGANIZATION_FOLLOW_IGNORE, ACTION_ORGANIZATION_STOP_FOLLOWING,
     ACTION_ORGANIZATION_STOP_IGNORING, ACTION_VOTER_GUIDE_VISIT]


logger = wevote_functions.admin.get_logger(__name__)


class AnalyticsAction(models.Model):
    """
    This is an incoming action we want to track
    """
    action_constant = models.PositiveSmallIntegerField(
        verbose_name="constant representing action", null=True, unique=False, db_index=True)

    exact_time = models.DateTimeField(verbose_name='date and time of action', null=False, auto_now_add=True)
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the action", null=True, unique=False, db_index=True)

    # We store both
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, default=None, null=True, blank=True, unique=False,
        db_index=True)
    voter_id = models.PositiveIntegerField(verbose_name="voter internal id", null=True, unique=False)

    # This voter is linked to a sign in account (Facebook, Twitter, Google, etc.)
    is_signed_in = models.BooleanField(verbose_name='', default=False)

    state_code = models.CharField(
        verbose_name="state_code", max_length=255, null=True, blank=True, unique=False)

    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False, db_index=True)
    organization_id = models.PositiveIntegerField(null=True, blank=True)

    ballot_item_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)

    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False, db_index=True)
    # This entry was the first entry on this day, used for tracking direct links to We Vote
    first_visit_today = models.BooleanField(verbose_name='', default=False)

    # We only want to store voter_device_id if we haven't verified the session yet. Set to null once verified.
    voter_device_id = models.CharField(
        verbose_name="voter_device_id of initiating voter", max_length=255, null=True, blank=True, unique=False)
    # When analytics comes into Analytics Application server, we need to authenticate the request. We authenticate
    #  the voter_device_id against a read-only database server, which might run seconds behind the master. Because of
    #  this, if a voter_device_id is not found the first time, we want to try again minutes later. BUT if that
    #  fails we want to invalidate the analytics.
    authentication_failed_twice = models.BooleanField(verbose_name='', default=False)
    user_agent = models.CharField(verbose_name="https request user agent", max_length=255, null=True, blank=True,
                                  unique=False)
    is_bot = models.BooleanField(verbose_name="request came from web-bots or spider", default=False)
    is_mobile = models.BooleanField(verbose_name="request came from mobile device", default=False)
    is_desktop = models.BooleanField(verbose_name="request came from desktop device", default=False)
    is_tablet = models.BooleanField(verbose_name="request came from tablet device", default=False)

    # We override the save function to auto-generate date_as_integer
    def save(self, *args, **kwargs):
        if self.date_as_integer:
            self.date_as_integer = convert_to_int(self.date_as_integer)
        if self.date_as_integer == "" or self.date_as_integer is None:  # If there isn't a value...
            self.generate_date_as_integer()
        super(AnalyticsAction, self).save(*args, **kwargs)

    def display_action_constant_human_readable(self):
        return display_action_constant_human_readable(self.action_constant)

    def generate_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        # We Vote uses Pacific Time for TIME_ZONE
        self.date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            logger.error("position.election Found multiple")
            return
        except Election.DoesNotExist:
            return
        except Exception as e:
            return
        return election

    def organization(self):
        if not self.organization_we_vote_id:
            return
        try:
            organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
        except Organization.MultipleObjectsReturned as e:
            logger.error("analytics.organization Found multiple")
            return
        except Organization.DoesNotExist:
            logger.error("analytics.organization did not find")
            return
        return organization


class AnalyticsCountManager(models.Manager):

    @staticmethod
    def fetch_ballot_views(google_civic_election_id=0, limit_to_one_date_as_integer=0):
        """
        Count the number of voters that viewed at least one ballot
        :param google_civic_election_id:
        :param limit_to_one_date_as_integer:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_organization_entrants_list(organization_we_vote_id, google_civic_election_id=0):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """

        voters_who_visited_organization_first_simple_list = []
        try:
            first_visit_query = AnalyticsAction.objects.using('analytics').all()
            first_visit_query = first_visit_query.filter(Q(action_constant=ACTION_VOTER_GUIDE_VISIT) |
                                                         Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            first_visit_query = first_visit_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(google_civic_election_id):
                first_visit_query = first_visit_query.filter(google_civic_election_id=google_civic_election_id)
            first_visit_query = first_visit_query.filter(first_visit_today=True)
            first_visit_query = first_visit_query.values('voter_we_vote_id').distinct()
            voters_who_visited_organization_first = list(first_visit_query)

            for voter_dict in voters_who_visited_organization_first:
                if positive_value_exists(voter_dict['voter_we_vote_id']):
                    voters_who_visited_organization_first_simple_list.append(voter_dict['voter_we_vote_id'])

        except Exception as e:
            pass

        return voters_who_visited_organization_first_simple_list

    def fetch_organization_entrants_took_position(
            self, organization_we_vote_id, google_civic_election_id=0):
        """
        Count the voters who entered on an organization's voter guide, and then took a position
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """

        voters_who_visited_organization_first_simple_list = \
            self.fetch_organization_entrants_list(organization_we_vote_id, google_civic_election_id)

        if not len(voters_who_visited_organization_first_simple_list):
            return 0

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_POSITION_TAKEN)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voters_who_visited_organization_first_simple_list)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    def fetch_organization_entrants_visited_ballot(
            self, organization_we_vote_id, google_civic_election_id=0):
        """
        Count the voters who entered on an organization's voter guide, and then who proceeded to ballot
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        voters_who_visited_organization_first_simple_list = \
            self.fetch_organization_entrants_list(organization_we_vote_id, google_civic_election_id)

        if not len(voters_who_visited_organization_first_simple_list):
            return 0

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voters_who_visited_organization_first_simple_list)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_organization_followers_took_position(organization_we_vote_id, google_civic_election_id=0):
        follow_organization_list = FollowOrganizationList()
        return_voter_we_vote_id = True
        voter_we_vote_ids_of_organization_followers = \
            follow_organization_list.fetch_followers_list_by_organization_we_vote_id(
                organization_we_vote_id, return_voter_we_vote_id)

        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_POSITION_TAKEN)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voter_we_vote_ids_of_organization_followers)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_organization_followers_visited_ballot(organization_we_vote_id, google_civic_election_id=0):
        follow_organization_list = FollowOrganizationList()
        return_voter_we_vote_id = True
        voter_we_vote_ids_of_organization_followers = \
            follow_organization_list.fetch_followers_list_by_organization_we_vote_id(
                organization_we_vote_id, return_voter_we_vote_id)
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(voter_we_vote_id__in=voter_we_vote_ids_of_organization_followers)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_visitors(
            google_civic_election_id=0,
            organization_we_vote_id='',
            limit_to_one_date_as_integer=0,
            count_through_this_date_as_integer=0,
            limit_to_authenticated=False):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            elif positive_value_exists(count_through_this_date_as_integer):
                count_query = count_query.filter(date_as_integer__lte=count_through_this_date_as_integer)
            if limit_to_authenticated:
                count_query = count_query.filter(is_signed_in=True)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_visitors_first_visit_to_organization_in_election(organization_we_vote_id, google_civic_election_id):
        """
        Entries are marked "first_visit_today" if it is the first visit in one day
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(Q(action_constant=ACTION_VOTER_GUIDE_VISIT) |
                                             Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(first_visit_today=True)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_new_followers_in_election(google_civic_election_id, organization_we_vote_id=""):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(Q(action_constant=ACTION_ORGANIZATION_FOLLOW) |
                                             Q(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW))
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_new_auto_followers_in_election(google_civic_election_id, organization_we_vote_id=""):
        """
        :param organization_we_vote_id:
        :param google_civic_election_id:
        :return:
        """
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(action_constant=ACTION_ORGANIZATION_AUTO_FOLLOW)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.values('voter_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_action_count(voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_ballot_visited(voter_we_vote_id, google_civic_election_id=0, organization_we_vote_id=''):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_BALLOT_VISIT)
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                count_query = count_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_welcome_visited(voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_WELCOME_VISIT)
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_days_visited(voter_we_vote_id):
        count_result = None
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.values('date_as_integer').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_last_action_date(voter_we_vote_id):
        last_action_date = None
        try:
            fetch_query = AnalyticsAction.objects.using('analytics').all()
            fetch_query = fetch_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            fetch_query = fetch_query.order_by('-id')
            fetch_query = fetch_query[:1]
            fetch_result = list(fetch_query)
            analytics_action = fetch_result.pop()
            last_action_date = analytics_action.exact_time
        except Exception as e:
            pass
        return last_action_date

    @staticmethod
    def fetch_voter_voter_guides_viewed(voter_we_vote_id):
        count_result = 0
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            count_query = count_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
            count_query = count_query.values('organization_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result

    @staticmethod
    def fetch_voter_guides_viewed(
            google_civic_election_id=0,
            limit_to_one_date_as_integer=0,
            count_through_this_date_as_integer=0):
        count_result = 0
        try:
            count_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                count_query = count_query.filter(google_civic_election_id=google_civic_election_id)
            count_query = count_query.filter(action_constant=ACTION_VOTER_GUIDE_VISIT)
            if positive_value_exists(limit_to_one_date_as_integer):
                count_query = count_query.filter(date_as_integer=limit_to_one_date_as_integer)
            elif positive_value_exists(count_through_this_date_as_integer):
                count_query = count_query.filter(date_as_integer__lte=count_through_this_date_as_integer)
            count_query = count_query.values('organization_we_vote_id').distinct()
            count_result = count_query.count()
        except Exception as e:
            pass
        return count_result


class AnalyticsManager(models.Manager):

    @staticmethod
    def create_action_type1(
            action_constant,
            voter_we_vote_id,
            voter_id,
            is_signed_in,
            state_code,
            organization_we_vote_id,
            organization_id,
            google_civic_election_id,
            user_agent_string,
            is_bot,
            is_mobile,
            is_desktop,
            is_tablet,
            ballot_item_we_vote_id="",
            voter_device_id=None):
        """
        Create AnalyticsAction data
        """
        success = True
        status = "ACTION_CONSTANT:" + display_action_constant_human_readable(action_constant) + " "
        action_saved = False
        action = AnalyticsAction()
        missing_required_variable = False

        if not action_constant:
            missing_required_variable = True
            status += 'MISSING_ACTION_CONSTANT '
        if not voter_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '
        if not organization_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_ORGANIZATION_WE_VOTE_ID '

        if missing_required_variable:
            results = {
                'success': success,
                'status': status,
                'action_saved': action_saved,
                'action': action,
            }
            return results

        try:
            action = AnalyticsAction.objects.using('analytics').create(
                action_constant=action_constant,
                voter_we_vote_id=voter_we_vote_id,
                voter_id=voter_id,
                is_signed_in=is_signed_in,
                state_code=state_code,
                organization_we_vote_id=organization_we_vote_id,
                organization_id=organization_id,
                google_civic_election_id=google_civic_election_id,
                ballot_item_we_vote_id=ballot_item_we_vote_id,
                user_agent=user_agent_string,
                is_bot=is_bot,
                is_mobile=is_mobile,
                is_desktop=is_desktop,
                is_tablet=is_tablet
            )
            success = True
            action_saved = True
            status += 'ACTION_TYPE1_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_ACTION_TYPE1: ' + str(e) + ' '

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    @staticmethod
    def create_action_type2(
            action_constant,
            voter_we_vote_id,
            voter_id,
            is_signed_in,
            state_code,
            organization_we_vote_id,
            google_civic_election_id,
            user_agent_string,
            is_bot,
            is_mobile,
            is_desktop,
            is_tablet,
            ballot_item_we_vote_id,
            voter_device_id=None):
        """
        Create AnalyticsAction data
        """
        success = True
        status = "ACTION_CONSTANT:" + display_action_constant_human_readable(action_constant) + " "
        action_saved = False
        action = AnalyticsAction()
        missing_required_variable = False

        if not action_constant:
            missing_required_variable = True
            status += 'MISSING_ACTION_CONSTANT '
        if not voter_we_vote_id:
            missing_required_variable = True
            status += 'MISSING_VOTER_WE_VOTE_ID '

        if missing_required_variable:
            results = {
                'success': success,
                'status': status,
                'action_saved': action_saved,
                'action': action,
            }
            return results

        try:
            action = AnalyticsAction.objects.using('analytics').create(
                action_constant=action_constant,
                voter_we_vote_id=voter_we_vote_id,
                voter_id=voter_id,
                is_signed_in=is_signed_in,
                state_code=state_code,
                organization_we_vote_id=organization_we_vote_id,
                google_civic_election_id=google_civic_election_id,
                ballot_item_we_vote_id=ballot_item_we_vote_id,
                user_agent=user_agent_string,
                is_bot=is_bot,
                is_mobile=is_mobile,
                is_desktop=is_desktop,
                is_tablet=is_tablet
            )
            success = True
            action_saved = True
            status += 'ACTION_TYPE2_SAVED '
        except Exception as e:
            success = False
            status += 'COULD_NOT_SAVE_ACTION_TYPE2: ' + str(e) + ' '

        results = {
            'success':      success,
            'status':       status,
            'action_saved': action_saved,
            'action':       action,
        }
        return results

    @staticmethod
    def retrieve_analytics_action_list(
            voter_we_vote_id='',
            voter_we_vote_id_list=[],
            google_civic_election_id=0,
            organization_we_vote_id='',
            action_constant='',
            distinct_for_members=False,
            state_code=''):
        success = True
        status = ""
        analytics_action_list = []

        try:
            list_query = AnalyticsAction.objects.using('analytics').all()
            if positive_value_exists(voter_we_vote_id):
                list_query = list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif len(voter_we_vote_id_list):
                list_query = list_query.filter(voter_we_vote_id__in=voter_we_vote_id_list)
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(action_constant):
                list_query = list_query.filter(action_constant=action_constant)
            if positive_value_exists(state_code):
                list_query = list_query.filter(state_code__iexact=state_code)
            if positive_value_exists(distinct_for_members):
                list_query = list_query.distinct(
                    'google_civic_election_id', 'organization_we_vote_id', 'voter_we_vote_id')
            analytics_action_list = list(list_query)
            analytics_action_list_found = positive_value_exists(len(analytics_action_list))
        except Exception as e:
            analytics_action_list_found = False
            status += "ANALYTICS_ACTION_LIST_ERROR: " + str(e) + " "
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'analytics_action_list':        analytics_action_list,
            'analytics_action_list_found':  analytics_action_list_found,
        }
        return results

    @staticmethod
    def retrieve_analytics_processed_list(
            analytics_date_as_integer=0,
            voter_we_vote_id='',
            voter_we_vote_id_list=[],
            google_civic_election_id=0,
            organization_we_vote_id='',
            kind_of_process='',
            batch_process_id=0,
            batch_process_analytics_chunk_id=0,
            analytics_date_as_integer_more_recent_than=0):
        success = True
        status = ""
        analytics_processed_list = []
        retrieved_voter_we_vote_id_list = []

        try:
            list_query = AnalyticsProcessed.objects.using('analytics').all()
            if positive_value_exists(batch_process_id):
                list_query = list_query.filter(batch_process_id=batch_process_id)
            if positive_value_exists(batch_process_analytics_chunk_id):
                list_query = list_query.filter(batch_process_analytics_chunk_id=batch_process_analytics_chunk_id)
            if positive_value_exists(analytics_date_as_integer_more_recent_than):
                list_query = list_query.filter(analytics_date_as_integer__gte=analytics_date_as_integer)
            elif positive_value_exists(analytics_date_as_integer):
                list_query = list_query.filter(analytics_date_as_integer=analytics_date_as_integer)
            if positive_value_exists(voter_we_vote_id):
                list_query = list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif len(voter_we_vote_id_list):
                list_query = list_query.filter(voter_we_vote_id__in=voter_we_vote_id_list)
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(kind_of_process):
                list_query = list_query.filter(kind_of_process__iexact=kind_of_process)

            voter_list_query = list_query
            analytics_processed_list = list(list_query)
            analytics_processed_list_found = True
        except Exception as e:
            analytics_processed_list_found = False
            status += "ANALYTICS_PROCESSED_LIST_ERROR: " + str(e) + " "
            success = False

        try:
            voter_list_query = voter_list_query.values_list('voter_we_vote_id', flat=True).distinct()
            retrieved_voter_we_vote_id_list = list(voter_list_query)
            retrieved_voter_we_vote_id_list_found = True
        except Exception as e:
            retrieved_voter_we_vote_id_list_found = False
            status += "ANALYTICS_PROCESSED_LIST_VOTER_WE_VOTE_ID_ERROR: " + str(e) + " "
            success = False

        results = {
            'success':                          success,
            'status':                           status,
            'analytics_processed_list':         analytics_processed_list,
            'analytics_processed_list_found':   analytics_processed_list_found,
            'retrieved_voter_we_vote_id_list':  retrieved_voter_we_vote_id_list,
            'retrieved_voter_we_vote_id_list_found':    retrieved_voter_we_vote_id_list_found,
        }
        return results

    @staticmethod
    def delete_analytics_processed_list(
            analytics_date_as_integer=0,
            voter_we_vote_id='',
            voter_we_vote_id_list=[],
            google_civic_election_id=0,
            organization_we_vote_id='',
            kind_of_process=''):
        success = True
        status = ""

        try:
            list_query = AnalyticsProcessed.objects.using('analytics').filter(
                analytics_date_as_integer=analytics_date_as_integer)
            if positive_value_exists(voter_we_vote_id):
                list_query = list_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            elif len(voter_we_vote_id_list):
                list_query = list_query.filter(voter_we_vote_id__in=voter_we_vote_id_list)
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            if positive_value_exists(organization_we_vote_id):
                list_query = list_query.filter(organization_we_vote_id__iexact=organization_we_vote_id)
            if positive_value_exists(kind_of_process):
                list_query = list_query.filter(kind_of_process__iexact=kind_of_process)
            list_query.delete()
            analytics_processed_list_deleted = True
        except Exception as e:
            analytics_processed_list_deleted = False
            status += "ANALYTICS_PROCESSED_LIST_ERROR: " + str(e) + " "
            success = False

        results = {
            'success':                      success,
            'status':                       status,
            'analytics_processed_list_deleted':  analytics_processed_list_deleted,
        }
        return results

    @staticmethod
    def save_analytics_processed(analytics_date_as_integer, voter_we_vote_id, defaults):
        success = True
        status = ""
        analytics_processed = None
        analytics_processed_saved = False

        try:
            analytics_processed, created = AnalyticsProcessed.objects.using('analytics').\
                update_or_create(
                    analytics_date_as_integer=analytics_date_as_integer,
                    voter_we_vote_id=voter_we_vote_id,
                    kind_of_process=defaults['kind_of_process'],
                    defaults=defaults
                )
            analytics_processed_saved = True
        except Exception as e:
            success = False
            status += 'SAVE_ANALYTICS_PROCESSED_PROBLEM: ' + str(e) + ' '

        results = {
            'success':          success,
            'status':           status,
            'analytics_processed_saved':    analytics_processed_saved,
            'analytics_processed':          analytics_processed,
        }
        return results

    @staticmethod
    def save_analytics_processing_status(analytics_date_as_integer, defaults):
        success = True
        status = ""
        analytics_processing_status = None
        analytics_processing_status_saved = False

        try:
            analytics_processing_status, created = AnalyticsProcessingStatus.objects.using('analytics').\
                update_or_create(
                    analytics_date_as_integer=analytics_date_as_integer,
                    defaults=defaults
                )
            analytics_processing_status_saved = True
        except Exception as e:
            success = False
            status += 'SAVE_ANALYTICS_PROCESSING_STATUS_PROBLEM: ' + str(e) + ' '

        results = {
            'success':          success,
            'status':           status,
            'analytics_processing_status_saved':    analytics_processing_status_saved,
            'analytics_processing_status':          analytics_processing_status,
        }
        return results

    @staticmethod
    def retrieve_analytics_processing_status_by_date_as_integer(analytics_date_as_integer):
        success = False
        status = ""

        try:
            analytics_processing_status = AnalyticsProcessingStatus.objects.using('analytics').get(
                analytics_date_as_integer=analytics_date_as_integer)
            analytics_processing_status_found = True
        except Exception as e:
            analytics_processing_status = None
            analytics_processing_status_found = False
            status += "RETRIEVE_ANALYTICS_PROCESSING_STATUS: " + str(e) + " "

        results = {
            'success':                              success,
            'status':                               status,
            'analytics_processing_status':          analytics_processing_status,
            'analytics_processing_status_found':    analytics_processing_status_found,
        }
        return results

    @staticmethod
    def find_next_date_with_analytics_to_process(last_analytics_date_as_integer):
        status = ""
        success = True
        times_tried = 0
        still_looking_for_next_date = True
        prior_analytics_date_as_integer = last_analytics_date_as_integer
        new_analytics_date_as_integer = 0
        new_analytics_date_as_integer_found = False

        # If here, these are all finished, and we need to analyze the next day
        date_now = now()
        date_now_as_integer = convert_date_to_date_as_integer(date_now)

        while still_looking_for_next_date:
            times_tried += 1
            if times_tried > 500:
                still_looking_for_next_date = False
                continue

            # Make sure the last date_as_integer analyzed isn't past today
            prior_analytics_date = convert_date_as_integer_to_date(prior_analytics_date_as_integer)
            one_day = timedelta(days=1)
            new_analytics_date = prior_analytics_date + one_day
            new_analytics_date_as_integer = convert_date_to_date_as_integer(new_analytics_date)

            if new_analytics_date_as_integer >= date_now_as_integer:
                new_analytics_date_as_integer_found = False
                status += "NEXT_ANALYTICS_DATE_IS_TODAY "
                results = {
                    'success':                              success,
                    'status':                               status,
                    'new_analytics_date_as_integer':        new_analytics_date_as_integer,
                    'new_analytics_date_as_integer_found':  new_analytics_date_as_integer_found,
                }
                return results

            # Now see if we have analytics on that date
            try:
                voter_history_query = AnalyticsAction.objects.using('analytics').all()
                voter_history_query = voter_history_query.filter(date_as_integer=new_analytics_date_as_integer)
                analytics_count = voter_history_query.count()
                if positive_value_exists(analytics_count):
                    still_looking_for_next_date = False
                    new_analytics_date_as_integer_found = True
                else:
                    prior_analytics_date_as_integer = new_analytics_date_as_integer
            except Exception as e:
                status += "COULD_NOT_RETRIEVE_ANALYTICS: " + str(e) + " "
                still_looking_for_next_date = False

        results = {
            'success':                              success,
            'status':                               status,
            'new_analytics_date_as_integer':        new_analytics_date_as_integer,
            'new_analytics_date_as_integer_found':  new_analytics_date_as_integer_found,
        }
        return results

    @staticmethod
    def does_analytics_processing_status_exist_for_one_date(analytics_date_as_integer_last_processed):
        status = ""
        success = True

        queryset = AnalyticsProcessingStatus.objects.using('analytics').order_by('analytics_date_as_integer')
        if positive_value_exists(analytics_date_as_integer_last_processed):
            # If there is a start date, force this query to only search before that date.
            # Go back and find the next date with analytics to process
            queryset = queryset.filter(analytics_date_as_integer=analytics_date_as_integer_last_processed)
        analytics_processing_status_list = queryset[:1]
        analytics_processing_status = None
        analytics_processing_status_found = False
        if len(analytics_processing_status_list):
            # We have found one to work on
            analytics_processing_status = analytics_processing_status_list[0]
            analytics_processing_status_found = True

        results = {
            'success':                              success,
            'status':                               status,
            'analytics_processing_status':          analytics_processing_status,
            'analytics_processing_status_found':    analytics_processing_status_found,
        }
        return results

    @staticmethod
    def request_unfinished_analytics_processing_status_for_one_date(analytics_date_as_integer_last_processed):
        status = ""
        success = True

        queryset = AnalyticsProcessingStatus.objects.using('analytics').order_by('analytics_date_as_integer')
        if positive_value_exists(analytics_date_as_integer_last_processed):
            # If there is a start date, force this query to only search before that date.
            # Go back and find the next date with analytics to process
            queryset = queryset.filter(analytics_date_as_integer=analytics_date_as_integer_last_processed)

        # Limit to entries that haven't been finished
        filters = []
        # AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID
        new_filter = Q(finished_augment_analytics_action_with_election_id=False)
        filters.append(new_filter)

        # AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT
        new_filter = Q(finished_augment_analytics_action_with_first_visit=False)
        filters.append(new_filter)

        # CALCULATE_ORGANIZATION_DAILY_METRICS
        # new_filter = Q(finished_calculate_organization_daily_metrics=False)
        # filters.append(new_filter)
        #
        # CALCULATE_ORGANIZATION_ELECTION_METRICS
        # new_filter = Q(finished_calculate_organization_election_metrics=False)
        # filters.append(new_filter)

        # CALCULATE_SITEWIDE_DAILY_METRICS
        new_filter = Q(finished_calculate_sitewide_daily_metrics=False)
        filters.append(new_filter)

        # CALCULATE_SITEWIDE_ELECTION_METRICS
        # new_filter = Q(finished_calculate_sitewide_election_metrics=False)
        # filters.append(new_filter)

        # CALCULATE_SITEWIDE_VOTER_METRICS
        new_filter = Q(finished_calculate_sitewide_voter_metrics=False)
        filters.append(new_filter)

        # Add the first query
        final_filters = filters.pop()
        # ...and "OR" the remaining items in the list
        for item in filters:
            final_filters |= item
        queryset = queryset.filter(final_filters)
        analytics_processing_status_list = queryset[:1]

        analytics_processing_status = None
        analytics_processing_status_found = False
        if len(analytics_processing_status_list):
            # We have found one to work on
            analytics_processing_status = analytics_processing_status_list[0]
            analytics_processing_status_found = True

        results = {
            'success':                              success,
            'status':                               status,
            'analytics_processing_status':          analytics_processing_status,
            'analytics_processing_status_found':    analytics_processing_status_found,
        }
        return results

    def retrieve_or_create_next_analytics_processing_status(self):
        """
        Find the highest (most recent) date_as_integer. If all elements have been completed,
        then create an entry for the next day. If not, return the latest entry.
        :return:
        """
        success = True
        status = ""
        analytics_processing_status = None
        analytics_processing_status_found = False
        create_new_status_entry = False
        new_analytics_date_as_integer = 0
        we_vote_settings_manager = WeVoteSettingsManager()
        results = we_vote_settings_manager.fetch_setting_results('analytics_date_as_integer_last_processed')
        analytics_date_as_integer_last_processed = 0
        if results['we_vote_setting_found']:
            analytics_date_as_integer_last_processed = convert_to_int(results['setting_value'])

        if not positive_value_exists(analytics_date_as_integer_last_processed):
            status += "analytics_date_as_integer_last_processed-MISSING "
            success = False
            results = {
                'success': success,
                'status': status,
                'analytics_processing_status': analytics_processing_status,
                'analytics_processing_status_found': analytics_processing_status_found,
            }
            return results

        try:
            # Is there an analytics_processing_status for the date we care about?
            results = self.does_analytics_processing_status_exist_for_one_date(analytics_date_as_integer_last_processed)
            if not results['analytics_processing_status_found']:
                # If here, kick off the processing of another day by creating "empty" AnalyticsProcessingStatus
                defaults = {}
                analytics_processing_status, created = AnalyticsProcessingStatus.objects.using('analytics').\
                    update_or_create(
                        analytics_date_as_integer=analytics_date_as_integer_last_processed,
                        defaults=defaults
                    )
            else:
                # Are there any tasks remaining on this date?
                results = self.request_unfinished_analytics_processing_status_for_one_date(
                    analytics_date_as_integer_last_processed)
                if results['analytics_processing_status_found']:
                    # We have found one to work on
                    analytics_processing_status = results['analytics_processing_status']
                    analytics_processing_status_found = True
                else:
                    if positive_value_exists(analytics_date_as_integer_last_processed):
                        # Check to see if there is any analytics activity on the day after
                        #  analytics_date_as_integer_last_processed
                        results = self.find_next_date_with_analytics_to_process(
                            last_analytics_date_as_integer=analytics_date_as_integer_last_processed)
                        if results['new_analytics_date_as_integer_found']:
                            new_analytics_date_as_integer = results['new_analytics_date_as_integer']
                            create_new_status_entry = True
                    else:
                        # Find last day processed with all calculations finished, so we advance to next available day
                        status += "NO_ANALYTICS_PROCESSING_STATUS_FOUND "
                        queryset = AnalyticsProcessingStatus.objects.using('analytics').\
                            order_by('-analytics_date_as_integer')
                        analytics_processing_status_list = queryset[:1]
                        if len(analytics_processing_status_list):
                            # We have found one to work on
                            analytics_processing_status = analytics_processing_status_list[0]
                            new_analytics_date_as_integer = analytics_processing_status.analytics_date_as_integer

        except Exception as e:
            analytics_processing_status_found = False
            status += "ANALYTICS_PROCESSING_STATUS_ERROR: " + str(e) + " "
            success = False

        if create_new_status_entry and positive_value_exists(new_analytics_date_as_integer) and success:
            # We don't want to proceed with the new date until we pass midnight US Pacific Time
            
            # timezone = pytz.timezone("America/Los_Angeles")
            # pacific_time_datetime_now = timezone.localize(datetime.now())
            # pacific_time_date_as_integer = convert_date_to_date_as_integer(pacific_time_datetime_now)
            pacific_time_date_as_integer = generate_localized_datetime_as_integer()

            if new_analytics_date_as_integer > pacific_time_date_as_integer:
                # Wait until we pass midnight to process the analytics
                status += "WAIT_UNTIL_AFTER_MIDNIGHT_PACIFIC_TIME "
                pass
            else:
                # If here, we need to create a new entry
                try:
                    defaults = {}
                    analytics_processing_status, created = AnalyticsProcessingStatus.objects.using('analytics').\
                        update_or_create(
                            analytics_date_as_integer=new_analytics_date_as_integer,
                            defaults=defaults
                        )
                    analytics_processing_status_found = True
                    status += "ANALYTICS_PROCESSING_STATUS_CREATED "

                    if positive_value_exists(new_analytics_date_as_integer):
                        # Update this value in the settings table: analytics_date_as_integer_last_processed
                        # ...to new_analytics_date_as_integer
                        results = we_vote_settings_manager.save_setting(
                            setting_name="analytics_date_as_integer_last_processed",
                            setting_value=new_analytics_date_as_integer,
                            value_type=WeVoteSetting.INTEGER)
                except Exception as e:
                    success = False
                    status += 'CREATE_ANALYTICS_PROCESSING_STATUS_ERROR: ' + str(e) + ' '

        results = {
            'success':                              success,
            'status':                               status,
            'analytics_processing_status':          analytics_processing_status,
            'analytics_processing_status_found':    analytics_processing_status_found,
        }
        return results

    @staticmethod
    def retrieve_organization_election_metrics_list(google_civic_election_id=0):
        success = False
        status = ""
        organization_election_metrics_list = []

        try:
            list_query = OrganizationElectionMetrics.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            organization_election_metrics_list = list(list_query)
            organization_election_metrics_list_found = True
        except Exception as e:
            organization_election_metrics_list_found = False
            success = False
            status += 'ORGANIZATION_ELECTION_METRICS_ERROR: ' + str(e) + ' '

        results = {
            'success':                      success,
            'status':                       status,
            'organization_election_metrics_list':        organization_election_metrics_list,
            'organization_election_metrics_list_found':  organization_election_metrics_list_found,
        }
        return results

    @staticmethod
    def retrieve_sitewide_election_metrics_list(google_civic_election_id=0):
        success = False
        status = ""
        sitewide_election_metrics_list = []

        try:
            list_query = SitewideElectionMetrics.objects.using('analytics').all()
            if positive_value_exists(google_civic_election_id):
                list_query = list_query.filter(google_civic_election_id=google_civic_election_id)
            sitewide_election_metrics_list = list(list_query)
            success = True
            sitewide_election_metrics_list_found = True
        except Exception as e:
            sitewide_election_metrics_list_found = False

        results = {
            'success':                      success,
            'status':                       status,
            'sitewide_election_metrics_list':        sitewide_election_metrics_list,
            'sitewide_election_metrics_list_found':  sitewide_election_metrics_list_found,
        }
        return results

    @staticmethod
    def retrieve_list_of_dates_with_actions(date_as_integer, through_date_as_integer=0):
        success = False
        status = ""
        date_list = []

        try:
            date_list_query = AnalyticsAction.objects.using('analytics').all()
            date_list_query = date_list_query.filter(date_as_integer__gte=date_as_integer)
            if positive_value_exists(through_date_as_integer):
                date_list_query = date_list_query.filter(date_as_integer__lte=through_date_as_integer)
            date_list_query = date_list_query.values('date_as_integer').distinct()
            date_list = list(date_list_query)
            date_list_found = True
        except Exception as e:
            date_list_found = False

        modified_date_list = []
        for date_as_integer_dict in date_list:
            if positive_value_exists(date_as_integer_dict['date_as_integer']):
                modified_date_list.append(date_as_integer_dict['date_as_integer'])

        results = {
            'success':                      success,
            'status':                       status,
            'date_as_integer_list':         modified_date_list,
            'date_as_integer_list_found':   date_list_found,
        }
        return results

    @staticmethod
    def retrieve_organization_list_with_election_activity(google_civic_election_id):
        success = False
        status = ""
        organization_list = []

        try:
            organization_list_query = AnalyticsAction.objects.using('analytics').all()
            organization_list_query = organization_list_query.filter(google_civic_election_id=google_civic_election_id)
            organization_list_query = organization_list_query.values('organization_we_vote_id').distinct()
            organization_list = list(organization_list_query)
            organization_list_found = True
        except Exception as e:
            organization_list_found = False

        modified_organization_list = []
        for organization_dict in organization_list:
            if positive_value_exists(organization_dict['organization_we_vote_id']):
                modified_organization_list.append(organization_dict['organization_we_vote_id'])

        results = {
            'success':                              success,
            'status':                               status,
            'organization_we_vote_id_list':         modified_organization_list,
            'organization_we_vote_id_list_found':   organization_list_found,
        }
        return results

    @staticmethod
    def retrieve_voter_we_vote_id_list_with_changes_since(date_as_integer, through_date_as_integer):
        success = True
        status = ""
        voter_list = []

        try:
            voter_list_query = AnalyticsAction.objects.using('analytics').all()
            voter_list_query = voter_list_query.filter(date_as_integer__gte=date_as_integer)
            voter_list_query = voter_list_query.filter(date_as_integer__lte=through_date_as_integer)
            voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
            # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
            voter_list = list(voter_list_query)
            voter_list_found = True
        except Exception as e:
            success = False
            voter_list_found = False

        modified_voter_list = []
        for voter_dict in voter_list:
            if positive_value_exists(voter_dict['voter_we_vote_id']):
                modified_voter_list.append(voter_dict['voter_we_vote_id'])

        results = {
            'success':                       success,
            'status':                        status,
            'voter_we_vote_id_list':         modified_voter_list,
            'voter_we_vote_id_list_found':   voter_list_found,
        }
        return results

    def save_action(self, action_constant="",
                    voter_we_vote_id="", voter_id=0, is_signed_in=False, state_code="",
                    organization_we_vote_id="", organization_id=0, google_civic_election_id=0,
                    user_agent_string="", is_bot=False, is_mobile=False, is_desktop=False, is_tablet=False,
                    ballot_item_we_vote_id="", voter_device_id=None):
        # If a voter_device_id is passed in, it is because this action may be coming from
        #  https://analytics.wevoteusa.org and hasn't been authenticated yet
        # Confirm that we have a valid voter_device_id. If not, store the action with the voter_device_id so we can
        #  look up later.

        # If either voter identifier comes in, make sure we have both

        # If either organization identifier comes in, make sure we have both

        if action_constant in ACTIONS_THAT_REQUIRE_ORGANIZATION_IDS:
            # In the future we could reduce clutter in the AnalyticsAction table by only storing one entry per day
            return self.create_action_type1(action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
                                            organization_we_vote_id, organization_id, google_civic_election_id,
                                            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
                                            ballot_item_we_vote_id, voter_device_id)
        else:
            return self.create_action_type2(action_constant, voter_we_vote_id, voter_id, is_signed_in, state_code,
                                            organization_we_vote_id, google_civic_election_id,
                                            user_agent_string, is_bot, is_mobile, is_desktop, is_tablet,
                                            ballot_item_we_vote_id, voter_device_id)

    @staticmethod
    def save_organization_daily_metrics_values(organization_daily_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = OrganizationDailyMetrics()
        missing_required_variables = False
        date_as_integer = 0
        organization_we_vote_id = ''

        if positive_value_exists(organization_daily_metrics_values['organization_we_vote_id']):
            organization_we_vote_id = organization_daily_metrics_values['organization_we_vote_id']
        else:
            missing_required_variables = True
        if positive_value_exists(organization_daily_metrics_values['date_as_integer']):
            date_as_integer = organization_daily_metrics_values['date_as_integer']
        else:
            missing_required_variables = True

        if not missing_required_variables:
            try:
                metrics_saved, created = OrganizationDailyMetrics.objects.using('analytics').update_or_create(
                    organization_we_vote_id=organization_we_vote_id,
                    date_as_integer=date_as_integer,
                    defaults=organization_daily_metrics_values
                )
            except Exception as e:
                success = False
                status += 'ORGANIZATION_DAILY_METRICS_UPDATE_OR_CREATE_FAILED ' + str(e) + ' '

        results = {
            'success':          success,
            'status':           status,
            'metrics_saved':    metrics_saved,
            'metrics':          metrics,
        }
        return results

    @staticmethod
    def save_organization_election_metrics_values(organization_election_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = OrganizationElectionMetrics()
        missing_required_variables = False
        google_civic_election_id = 0
        organization_we_vote_id = ''

        if positive_value_exists(organization_election_metrics_values['google_civic_election_id']):
            google_civic_election_id = organization_election_metrics_values['google_civic_election_id']
        else:
            missing_required_variables = True
        if positive_value_exists(organization_election_metrics_values['organization_we_vote_id']):
            organization_we_vote_id = organization_election_metrics_values['organization_we_vote_id']
        else:
            missing_required_variables = True

        if not missing_required_variables:
            try:
                metrics_saved, created = OrganizationElectionMetrics.objects.using('analytics').update_or_create(
                    google_civic_election_id=google_civic_election_id,
                    organization_we_vote_id__iexact=organization_we_vote_id,
                    defaults=organization_election_metrics_values
                )
            except Exception as e:
                success = False
                status += 'ORGANIZATION_ELECTION_METRICS_UPDATE_OR_CREATE_FAILED ' + str(e) + ' '

        results = {
            'success':          success,
            'status':           status,
            'metrics_saved':    metrics_saved,
            'metrics':          metrics,
        }
        return results

    @staticmethod
    def save_sitewide_daily_metrics_values(sitewide_daily_metrics_values):
        success = True
        status = ""
        sitewide_daily_metrics_saved = False
        sitewide_daily_metrics = SitewideDailyMetrics()

        if positive_value_exists(sitewide_daily_metrics_values['date_as_integer']):
            date_as_integer = sitewide_daily_metrics_values['date_as_integer']

            try:
                sitewide_daily_metrics, created = SitewideDailyMetrics.objects.using('analytics').update_or_create(
                    date_as_integer=date_as_integer,
                    defaults=sitewide_daily_metrics_values
                )
                sitewide_daily_metrics_saved = True
            except Exception as e:
                success = False
                status += 'SITEWIDE_DAILY_METRICS_UPDATE_OR_CREATE_FAILED ' \
                          '(' + str(date_as_integer) + '): ' + str(e) + ' '
        else:
            status += "SITEWIDE_DAILY_METRICS-MISSING_DATE_AS_INTEGER "

        results = {
            'success':                      success,
            'status':                       status,
            'sitewide_daily_metrics_saved': sitewide_daily_metrics_saved,
            'sitewide_daily_metrics':       sitewide_daily_metrics,
        }
        return results

    @staticmethod
    def save_sitewide_election_metrics_values(sitewide_election_metrics_values):
        success = False
        status = ""
        metrics_saved = False
        metrics = SitewideElectionMetrics()

        if positive_value_exists(sitewide_election_metrics_values['google_civic_election_id']):
            google_civic_election_id = sitewide_election_metrics_values['google_civic_election_id']

            try:
                metrics_saved, created = SitewideElectionMetrics.objects.using('analytics').update_or_create(
                    google_civic_election_id=google_civic_election_id,
                    defaults=sitewide_election_metrics_values
                )
            except Exception as e:
                success = False
                status += 'SITEWIDE_ELECTION_METRICS_UPDATE_OR_CREATE_FAILED ' + str(e) + ' '

        results = {
            'success': success,
            'status': status,
            'metrics_saved': metrics_saved,
            'metrics': metrics,
        }
        return results

    @staticmethod
    def save_sitewide_voter_metrics_values_for_one_voter(sitewide_voter_metrics_values):
        success = False
        status = ""
        metrics_saved = False

        if positive_value_exists(sitewide_voter_metrics_values['voter_we_vote_id']):
            voter_we_vote_id = sitewide_voter_metrics_values['voter_we_vote_id']

            try:
                metrics_saved, created = SitewideVoterMetrics.objects.using('analytics').update_or_create(
                    voter_we_vote_id__iexact=voter_we_vote_id,
                    defaults=sitewide_voter_metrics_values
                )
                success = True
            except Exception as e:
                success = False
                status += 'SITEWIDE_VOTER_METRICS_UPDATE_OR_CREATE_FAILED ' + str(e) + ' '
                results = {
                    'success': success,
                    'status': status,
                    'metrics_saved': metrics_saved,
                }
                return results

        else:
            status += "SITEWIDE_VOTER_METRICS_SAVE-MISSING_VOTER_WE_VOTE_ID "

        results = {
            'success': success,
            'status': status,
            'metrics_saved': metrics_saved,
        }
        return results

    @staticmethod
    def sitewide_voter_metrics_for_this_voter_updated_this_date(voter_we_vote_id, updated_date_integer):
        updated_on_date_query = SitewideVoterMetrics.objects.using('analytics').filter(
            voter_we_vote_id__iexact=voter_we_vote_id,
            last_calculated_date_as_integer=updated_date_integer
        )
        return positive_value_exists(updated_on_date_query.count())

    @staticmethod
    def update_first_visit_today_for_all_voters_since_date(date_as_integer, through_date_as_integer):
        success = True
        status = ""
        distinct_days_list = []
        first_visit_today_count = 0

        # Get distinct days
        try:
            distinct_days_query = AnalyticsAction.objects.using('analytics').all()
            distinct_days_query = distinct_days_query.filter(date_as_integer__gte=date_as_integer)
            distinct_days_query = distinct_days_query.filter(date_as_integer__lte=through_date_as_integer)
            distinct_days_query = distinct_days_query.values('date_as_integer').distinct()
            # distinct_days_query = distinct_days_query[:5]  # TEMP limit to 5
            distinct_days_list = list(distinct_days_query)
            distinct_days_found = True
        except Exception as e:
            success = False
            status += "UPDATE_FIRST_VISIT_TODAY-DISTINCT_DAY_QUERY_ERROR " + str(e) + ' '
            distinct_days_found = False

        simple_distinct_days_list = []
        for day_dict in distinct_days_list:
            if positive_value_exists(day_dict['date_as_integer']):
                simple_distinct_days_list.append(day_dict['date_as_integer'])

        # Loop through each day
        for one_date_as_integer in simple_distinct_days_list:
            # Get distinct voters on that day
            if not positive_value_exists(one_date_as_integer):
                continue

            voter_list = []
            try:
                voter_list_query = AnalyticsAction.objects.using('analytics').all()
                voter_list_query = voter_list_query.filter(date_as_integer=one_date_as_integer)
                voter_list_query = voter_list_query.values('voter_we_vote_id').distinct()
                # voter_list_query = voter_list_query[:5]  # TEMP limit to 5
                voter_list = list(voter_list_query)
                voter_list_found = True
            except Exception as e:
                success = False
                status += "UPDATE_FIRST_VISIT_TODAY-DISTINCT_VOTER_QUERY_ERROR " + str(e) + ' '
                voter_list_found = False

            simple_voter_list = []
            for voter_dict in voter_list:
                if positive_value_exists(voter_dict['voter_we_vote_id']) and \
                        voter_dict['voter_we_vote_id'] not in simple_voter_list:
                    simple_voter_list.append(voter_dict['voter_we_vote_id'])

            if not voter_list_found:
                continue

            # Loop through each voter per day, and update the first entry for that day with "first_visit_today=True"
            for voter_we_vote_id in simple_voter_list:
                if not positive_value_exists(voter_we_vote_id):
                    continue

                try:
                    first_visit_query = AnalyticsAction.objects.using('analytics').all()
                    first_visit_query = first_visit_query.order_by("id")  # order by oldest first
                    first_visit_query = first_visit_query.filter(date_as_integer=one_date_as_integer)
                    first_visit_query = first_visit_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                    analytics_action = first_visit_query.first()

                    if not analytics_action.first_visit_today:
                        analytics_action.first_visit_today = True
                        analytics_action.save()
                        first_visit_saved = True
                        first_visit_today_count += 1
                except Exception as e:
                    success = False
                    status += "UPDATE_FIRST_VISIT_TODAY-VOTER_ON_DATE_QUERY_ERROR " + str(e) + ' '
                    print_to_log(logger=logger, exception_message_optional=status)
                    first_visit_found = False

        results = {
            'success':                  success,
            'status':                   status,
            'first_visit_today_count':  first_visit_today_count,
        }
        return results

    @staticmethod
    def update_first_visit_today_for_one_voter(voter_we_vote_id):
        success = False
        status = ""
        distinct_days_list = []
        first_visit_today_count = 0

        # Get distinct days
        try:
            distinct_days_query = AnalyticsAction.objects.using('analytics').all()
            distinct_days_query = distinct_days_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
            distinct_days_query = distinct_days_query.values('date_as_integer').distinct()
            distinct_days_list = list(distinct_days_query)
        except Exception as e:
            pass

        simple_distinct_days_list = []
        for day_dict in distinct_days_list:
            if positive_value_exists(day_dict['date_as_integer']):
                simple_distinct_days_list.append(day_dict['date_as_integer'])

        # Loop through each day
        for one_date_as_integer in simple_distinct_days_list:
            try:
                first_visit_query = AnalyticsAction.objects.using('analytics').all()
                first_visit_query = first_visit_query.order_by("id")  # order by oldest first
                first_visit_query = first_visit_query.filter(date_as_integer=one_date_as_integer)
                first_visit_query = first_visit_query.filter(voter_we_vote_id__iexact=voter_we_vote_id)
                analytics_action = first_visit_query.first()

                analytics_action.first_visit_today = True
                analytics_action.save()
                first_visit_today_count += 1
            except Exception as e:
                pass

        results = {
            'success': success,
            'status': status,
            'first_visit_today_count': first_visit_today_count,
        }
        return results


class AnalyticsProcessingStatus(models.Model):
    """
    When we have finished analyzing one element of the analytics data for a day, store our completion here
    """
    analytics_date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD", null=False, unique=True)
    # AUGMENT_ANALYTICS_ACTION_WITH_ELECTION_ID
    finished_augment_analytics_action_with_election_id = models.BooleanField(default=False)
    # AUGMENT_ANALYTICS_ACTION_WITH_FIRST_VISIT
    finished_augment_analytics_action_with_first_visit = models.BooleanField(default=False)
    # CALCULATE_ORGANIZATION_DAILY_METRICS
    finished_calculate_organization_daily_metrics = models.BooleanField(default=False)
    # CALCULATE_ORGANIZATION_ELECTION_METRICS
    finished_calculate_organization_election_metrics = models.BooleanField(default=False)
    # CALCULATE_SITEWIDE_DAILY_METRICS
    finished_calculate_sitewide_daily_metrics = models.BooleanField(default=False)
    # CALCULATE_SITEWIDE_ELECTION_METRICS
    finished_calculate_sitewide_election_metrics = models.BooleanField(default=False)
    # CALCULATE_SITEWIDE_VOTER_METRICS
    finished_calculate_sitewide_voter_metrics = models.BooleanField(default=False)


class AnalyticsProcessed(models.Model):
    """
    When we have finished analyzing one element of the analytics data for a day, store our completion here
    """
    analytics_date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD", null=False, unique=False)
    batch_process_id = models.PositiveIntegerField(null=True, unique=False)
    batch_process_analytics_chunk_id = models.PositiveIntegerField(null=True, unique=False)
    organization_we_vote_id = models.CharField(max_length=255, null=True, blank=True, unique=False)
    google_civic_election_id = models.PositiveIntegerField(null=True, unique=False)
    voter_we_vote_id = models.CharField(max_length=255, null=True, unique=False)
    kind_of_process = models.CharField(max_length=50, null=True, unique=False)


class OrganizationDailyMetrics(models.Model):
    """
    This is a summary of the organization activity on one day.
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD of the action",
                                                  null=True, unique=False, db_index=True)
    organization_we_vote_id = models.CharField(verbose_name="we vote permanent id",
                                               max_length=255, null=True, blank=True, unique=False)
    visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time", null=True, unique=False)
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today", null=True, unique=False)
    authenticated_visitors_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_visitors_today = models.PositiveIntegerField(verbose_name="new visitors, today", null=True, unique=False)

    voter_guide_entrants_today = models.PositiveIntegerField(verbose_name="first touch, voter guide",
                                                             null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_visiting_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_visiting_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    followers_total = models.PositiveIntegerField(verbose_name="all time",
                                                  null=True, unique=False)
    new_followers_today = models.PositiveIntegerField(verbose_name="today",
                                                      null=True, unique=False)

    auto_followers_total = models.PositiveIntegerField(verbose_name="all",
                                                       null=True, unique=False)
    new_auto_followers_today = models.PositiveIntegerField(verbose_name="today",
                                                           null=True, unique=False)

    issues_linked_total = models.PositiveIntegerField(verbose_name="organization classifications, all time",
                                                      null=True, unique=False)

    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)

    def generate_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        # We Vote uses Pacific Time for TIME_ZONE
        self.date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return


class OrganizationElectionMetrics(models.Model):
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)
    organization_we_vote_id = models.CharField(
        verbose_name="we vote permanent id", max_length=255, null=True, blank=True, unique=False)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entrants = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_at_time_of_election = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_followers = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    new_auto_followers = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_visited_ballot = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    entrants_took_position = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entrants_friends_only_positions_with_comments = models.PositiveIntegerField(
        verbose_name="", null=True, unique=False)

    followers_took_position = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    followers_friends_only_positions_with_comments = models.PositiveIntegerField(
        verbose_name="", null=True, unique=False)

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            # We retrieve this from the read-only database (as opposed to the analytics database)
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            return
        except Election.DoesNotExist:
            return
        except Exception as e:
            return
        return election

    def organization(self):
        if positive_value_exists(self.organization_we_vote_id):
            try:
                organization = Organization.objects.using('readonly').get(we_vote_id=self.organization_we_vote_id)
            except Organization.MultipleObjectsReturned as e:
                logger.error("analytics.organization Found multiple")
                return
            except Organization.DoesNotExist:
                logger.error("analytics.organization did not find")
                return
            return organization
        else:
            return Organization()


class SitewideDailyMetrics(models.Model):
    """
    This is a summary of the sitewide activity on one day.
    """
    # We store YYYYMMDD as an integer for very fast lookup (ex/ "20170901" for September, 1, 2017)
    date_as_integer = models.PositiveIntegerField(verbose_name="YYYYMMDD of the action",
                                                  null=True, unique=False, db_index=True)
    visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time", null=True, unique=False)
    visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today", null=True, unique=False)
    new_visitors_today = models.PositiveIntegerField(verbose_name="new visitors, today", null=True, unique=False)

    voter_guide_entrants_today = models.PositiveIntegerField(verbose_name="first touch, voter guide",
                                                             null=True, unique=False)
    welcome_page_entrants_today = models.PositiveIntegerField(verbose_name="first touch, welcome page",
                                                              null=True, unique=False)
    friend_entrants_today = models.PositiveIntegerField(verbose_name="first touch, response to friend",
                                                        null=True, unique=False)

    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="number of visitors, all time",
                                                               null=True, unique=False)
    authenticated_visitors_today = models.PositiveIntegerField(verbose_name="number of visitors, today",
                                                               null=True, unique=False)

    ballot_views_today = models.PositiveIntegerField(verbose_name="number of voters who viewed a ballot today",
                                                     null=True, unique=False)
    voter_guides_viewed_total = models.PositiveIntegerField(verbose_name="number of voter guides viewed, all time",
                                                            null=True, unique=False)
    voter_guides_viewed_today = models.PositiveIntegerField(verbose_name="number of voter guides viewed, today",
                                                            null=True, unique=False)

    issues_followed_total = models.PositiveIntegerField(verbose_name="number of issues followed, all time",
                                                        null=True, unique=False)
    issues_followed_today = models.PositiveIntegerField(verbose_name="issues followed today, today",
                                                        null=True, unique=False)

    issue_follows_total = models.PositiveIntegerField(verbose_name="one follow for one issue, all time",
                                                      null=True, unique=False)
    issue_follows_today = models.PositiveIntegerField(verbose_name="one follow for one issue, today",
                                                      null=True, unique=False)

    organizations_followed_total = models.PositiveIntegerField(verbose_name="voter follow organizations, all time",
                                                               null=True, unique=False)
    organizations_followed_today = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                               null=True, unique=False)

    organizations_auto_followed_total = models.PositiveIntegerField(verbose_name="auto_follow organizations, all",
                                                                    null=True, unique=False)
    organizations_auto_followed_today = models.PositiveIntegerField(verbose_name="auto_follow organizations, today",
                                                                    null=True, unique=False)

    organizations_with_linked_issues = models.PositiveIntegerField(verbose_name="organizations linked to issues, all",
                                                                   null=True, unique=False)

    issues_linked_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    issues_linked_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    organizations_signed_in_total = models.PositiveIntegerField(verbose_name="organizations signed in, all",
                                                                null=True, unique=False)

    organizations_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                               null=True, unique=False)
    organizations_with_new_positions_today = models.PositiveIntegerField(verbose_name="today",
                                                                         null=True, unique=False)
    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)
    individuals_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                             null=True, unique=False)
    individuals_with_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                    null=True, unique=False)
    individuals_with_friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                                          null=True, unique=False)
    friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                         null=True, unique=False)
    entered_full_address = models.PositiveIntegerField(verbose_name="all",
                                                       null=True, unique=False)

    shared_items_clicked_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    shared_link_clicked_count_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    shared_link_clicked_unique_viewers_today = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    def generate_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        # We Vote uses Pacific Time for TIME_ZONE
        self.date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return


class SitewideElectionMetrics(models.Model):
    """
    This is a summary of the sitewide activity for one election.
    """
    # The unique ID of this election. (Provided by Google Civic)
    google_civic_election_id = models.PositiveIntegerField(
        verbose_name="google civic election id", null=True, unique=False)
    election_day_text = models.CharField(verbose_name="election day", max_length=255, null=True, blank=True)
    visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    authenticated_visitors_total = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_entries = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    voter_guide_views = models.PositiveIntegerField(verbose_name="one person viewed one voter guide, this election",
                                                    null=True, unique=False)
    voter_guides_viewed = models.PositiveIntegerField(verbose_name="one org, seen at least once, this election",
                                                      null=True, unique=False)

    issues_followed = models.PositiveIntegerField(verbose_name="follow issue connections, all time",
                                                  null=True, unique=False)

    unique_voters_that_followed_organizations = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    unique_voters_that_auto_followed_organizations = models.PositiveIntegerField(verbose_name="",
                                                                                 null=True, unique=False)
    organizations_followed = models.PositiveIntegerField(verbose_name="voter follow organizations, today",
                                                         null=True, unique=False)
    organizations_auto_followed = models.PositiveIntegerField(verbose_name="auto_follow organizations, today",
                                                              null=True, unique=False)
    organizations_signed_in = models.PositiveIntegerField(verbose_name="organizations signed in, all",
                                                          null=True, unique=False)

    organizations_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                               null=True, unique=False)
    organization_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                null=True, unique=False)
    individuals_with_positions = models.PositiveIntegerField(verbose_name="all",
                                                             null=True, unique=False)
    individuals_with_public_positions = models.PositiveIntegerField(verbose_name="all",
                                                                    null=True, unique=False)
    individuals_with_friends_only_positions = models.PositiveIntegerField(verbose_name="all",
                                                                          null=True, unique=False)
    public_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    public_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    friends_only_positions = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    friends_only_positions_with_comments = models.PositiveIntegerField(verbose_name="", null=True, unique=False)
    entered_full_address = models.PositiveIntegerField(verbose_name="", null=True, unique=False)

    def election(self):
        if not self.google_civic_election_id:
            return
        try:
            # We retrieve this from the read-only database (as opposed to the analytics database)
            election = Election.objects.using('readonly').get(google_civic_election_id=self.google_civic_election_id)
        except Election.MultipleObjectsReturned as e:
            return
        except Election.DoesNotExist:
            return
        except Exception as e:
            return
        return election

    def generate_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        # We Vote uses Pacific Time for TIME_ZONE
        self.date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return


class SitewideVoterMetrics(models.Model):
    """
    A single entry per voter summarizing all activity every done on We Vote
    """
    voter_we_vote_id = models.CharField(
        verbose_name="we vote permanent id",
        max_length=255, default=None, null=True, blank=True, unique=False, db_index=True)
    actions_count = models.PositiveIntegerField(verbose_name="all", null=True, unique=False, db_index=True)
    elections_viewed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    voter_guides_viewed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    ballot_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    welcome_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False, db_index=True)
    entered_full_address = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    issues_followed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    organizations_followed = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    time_until_sign_in = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    positions_entered_friends_only = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    positions_entered_public = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    comments_entered_friends_only = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    comments_entered_public = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    signed_in_twitter = models.BooleanField(verbose_name='', default=False)
    signed_in_facebook = models.BooleanField(verbose_name='', default=False)
    signed_in_with_email = models.BooleanField(verbose_name='', default=False)
    signed_in_with_sms_phone_number = models.BooleanField(verbose_name='', default=False)
    seconds_on_site = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    days_visited = models.PositiveIntegerField(verbose_name="all", null=True, unique=False)
    last_action_date = models.DateTimeField(verbose_name='last action date and time', null=True, db_index=True)
    last_calculated_date_as_integer = models.PositiveIntegerField(
        verbose_name="YYYYMMDD of the last time stats calculated", null=True, unique=False, db_index=True)

    def generate_last_calculated_date_as_integer(self):
        # We want to store the day as an integer for extremely quick database indexing and lookup
        # We Vote uses Pacific Time for TIME_ZONE
        self.last_calculated_date_as_integer = wevote_functions.functions_date.generate_date_as_integer()
        return


def display_action_constant_human_readable(action_constant):
    if action_constant == ACTION_ABOUT_GETTING_STARTED:
        return "ABOUT_GETTING_STARTED"
    if action_constant == ACTION_ABOUT_MOBILE:
        return "ABOUT_MOBILE"
    if action_constant == ACTION_ABOUT_ORGANIZATION:
        return "ABOUT_ORGANIZATION"
    if action_constant == ACTION_ABOUT_TEAM:
        return "ABOUT_TEAM"
    if action_constant == ACTION_ABOUT_VISION:
        return "ABOUT_VISION"
    if action_constant == ACTION_ACCOUNT_PAGE:
        return "ACCOUNT_PAGE"
    if action_constant == ACTION_BALLOT_VISIT:
        return "BALLOT_VISIT"
    if action_constant == ACTION_CANDIDATE:
        return "CANDIDATE"
    if action_constant == ACTION_DONATE_VISIT:
        return "DONATE_VISIT"
    if action_constant == ACTION_ELECTIONS:
        return "ELECTIONS"
    if action_constant == ACTION_EMAIL_AUTHENTICATION_EXISTS:
        return "EMAIL_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_FACEBOOK_AUTHENTICATION_EXISTS:
        return "FACEBOOK_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_FACEBOOK_INVITABLE_FRIENDS:
        return "FACEBOOK_INVITABLE_FRIENDS"
    if action_constant == ACTION_FRIEND_ENTRY:
        return "FRIEND_ENTRY"
    if action_constant == ACTION_GOOGLE_AUTHENTICATION_EXISTS:
        return "GOOGLE_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_INVITE_BY_EMAIL:
        return "INVITE_BY_EMAIL"
    if action_constant == ACTION_ISSUE_FOLLOW:
        return "ISSUE_FOLLOW"
    if action_constant == ACTION_ISSUE_FOLLOW_IGNORE:
        return "ISSUE_FOLLOW_IGNORE"
    if action_constant == ACTION_ISSUE_STOP_FOLLOWING:
        return "ISSUE_STOP_FOLLOWING"
    if action_constant == ACTION_MEASURE:
        return "MEASURE"
    if action_constant == ACTION_MODAL_ISSUES:
        return "MODAL_ISSUES"
    if action_constant == ACTION_MODAL_ORGANIZATIONS:
        return "MODAL_ORGANIZATIONS"
    if action_constant == ACTION_MODAL_POSITIONS:
        return "MODAL_POSITIONS"
    if action_constant == ACTION_MODAL_FRIENDS:
        return "MODAL_FRIENDS"
    if action_constant == ACTION_MODAL_SHARE:
        return "MODAL_SHARE"
    if action_constant == ACTION_MODAL_VOTE:
        return "MODAL_VOTE"
    if action_constant == ACTION_MODAL_VOTER_PLAN:
        return "MODAL_VOTER_PLAN"
    if action_constant == ACTION_NETWORK:
        return "NETWORK"
    if action_constant == ACTION_NEWS:
        return "NEWS"
    if action_constant == ACTION_OFFICE:
        return "OFFICE"
    if action_constant == ACTION_ORGANIZATION_AUTO_FOLLOW:
        return "ORGANIZATION_AUTO_FOLLOW"
    if action_constant == ACTION_ORGANIZATION_FOLLOW:
        return "ORGANIZATION_FOLLOW"
    if action_constant == ACTION_ORGANIZATION_FOLLOW_IGNORE:
        return "ORGANIZATION_FOLLOW_IGNORE"
    if action_constant == ACTION_ORGANIZATION_STOP_FOLLOWING:
        return "ORGANIZATION_STOP_FOLLOWING"
    if action_constant == ACTION_ORGANIZATION_STOP_IGNORING:
        return "ORGANIZATION_STOP_IGNORING"
    if action_constant == ACTION_POSITION_TAKEN:
        return "POSITION_TAKEN"
    if action_constant == ACTION_READY_VISIT:
        return "READY_VISIT"
    if action_constant == ACTION_SEARCH_OPINIONS:
        return "SEARCH_OPINIONS"
    if action_constant == ACTION_SELECT_BALLOT_MODAL:
        return "SELECT_BALLOT_MODAL"
    if action_constant == ACTION_SHARE_BUTTON_COPY:
        return "SHARE_BUTTON_COPY"
    if action_constant == ACTION_SHARE_BUTTON_EMAIL:
        return "SHARE_BUTTON_EMAIL"
    if action_constant == ACTION_SHARE_BUTTON_FACEBOOK:
        return "SHARE_BUTTON_FACEBOOK"
    if action_constant == ACTION_SHARE_BUTTON_FRIENDS:
        return "SHARE_BUTTON_FRIENDS"
    if action_constant == ACTION_SHARE_BUTTON_TWITTER:
        return "SHARE_BUTTON_TWITTER"
    if action_constant == ACTION_SHARE_BALLOT:
        return "SHARE_BALLOT"
    if action_constant == ACTION_SHARE_BALLOT_ALL_OPINIONS:
        return "SHARE_BALLOT_ALL_OPINIONS"
    if action_constant == ACTION_SHARE_CANDIDATE:
        return "SHARE_CANDIDATE"
    if action_constant == ACTION_SHARE_CANDIDATE_ALL_OPINIONS:
        return "SHARE_CANDIDATE_ALL_OPINIONS"
    if action_constant == ACTION_SHARE_MEASURE:
        return "SHARE_MEASURE"
    if action_constant == ACTION_SHARE_MEASURE_ALL_OPINIONS:
        return "SHARE_MEASURE_ALL_OPINIONS"
    if action_constant == ACTION_SHARE_OFFICE:
        return "SHARE_OFFICE"
    if action_constant == ACTION_SHARE_OFFICE_ALL_OPINIONS:
        return "SHARE_OFFICE_ALL_OPINIONS"
    if action_constant == ACTION_SHARE_ORGANIZATION:
        return "SHARE_ORGANIZATION"
    if action_constant == ACTION_SHARE_ORGANIZATION_ALL_OPINIONS:
        return "SHARE_ORGANIZATION_ALL_OPINIONS"
    if action_constant == ACTION_SHARE_READY:
        return "SHARE_READY"
    if action_constant == ACTION_SHARE_READY_ALL_OPINIONS:
        return "SHARE_READY_ALL_OPINIONS"
    if action_constant == ACTION_TWITTER_AUTHENTICATION_EXISTS:
        return "TWITTER_AUTHENTICATION_EXISTS"
    if action_constant == ACTION_UNSUBSCRIBE_EMAIL_PAGE:
        return "UNSUBSCRIBE_EMAIL_PAGE"
    if action_constant == ACTION_UNSUBSCRIBE_SMS_PAGE:
        return "UNSUBSCRIBE_SMS_PAGE"
    if action_constant == ACTION_VIEW_SHARED_BALLOT:
        return "VIEW_SHARED_BALLOT"
    if action_constant == ACTION_VIEW_SHARED_BALLOT_ALL_OPINIONS:
        return "VIEW_SHARED_BALLOT_ALL_OPINIONS"
    if action_constant == ACTION_VIEW_SHARED_CANDIDATE:
        return "VIEW_SHARED_CANDIDATE"
    if action_constant == ACTION_VIEW_SHARED_CANDIDATE_ALL_OPINIONS:
        return "VIEW_SHARED_CANDIDATE_ALL_OPINIONS"
    if action_constant == ACTION_VIEW_SHARED_MEASURE:
        return "VIEW_SHARED_MEASURE"
    if action_constant == ACTION_VIEW_SHARED_MEASURE_ALL_OPINIONS:
        return "VIEW_SHARED_MEASURE_ALL_OPINIONS"
    if action_constant == ACTION_VIEW_SHARED_OFFICE:
        return "VIEW_SHARED_OFFICE"
    if action_constant == ACTION_VIEW_SHARED_OFFICE_ALL_OPINIONS:
        return "VIEW_SHARED_OFFICE_ALL_OPINIONS"
    if action_constant == ACTION_VIEW_SHARED_ORGANIZATION:
        return "VIEW_SHARED_ORGANIZATION"
    if action_constant == ACTION_VIEW_SHARED_ORGANIZATION_ALL_OPINIONS:
        return "VIEW_SHARED_ORGANIZATION_ALL_OPINIONS"
    if action_constant == ACTION_VIEW_SHARED_READY:
        return "VIEW_SHARED_READY"
    if action_constant == ACTION_VIEW_SHARED_READY_ALL_OPINIONS:
        return "VIEW_SHARED_READY_ALL_OPINIONS"
    if action_constant == ACTION_VOTER_FACEBOOK_AUTH:
        return "VOTER_FACEBOOK_AUTH"
    if action_constant == ACTION_VOTER_GUIDE_ENTRY:
        return "VOTER_GUIDE_ENTRY"
    if action_constant == ACTION_VOTER_GUIDE_GET_STARTED:
        return "VOTER_GUIDE_GET_STARTED"
    if action_constant == ACTION_VOTER_GUIDE_VISIT:
        return "VOTER_GUIDE_VISIT"
    if action_constant == ACTION_VOTER_TWITTER_AUTH:
        return "VOTER_TWITTER_AUTH"
    if action_constant == ACTION_WELCOME_ENTRY:
        return "WELCOME_ENTRY"
    if action_constant == ACTION_WELCOME_VISIT:
        return "WELCOME_VISIT"

    return "ACTION_CONSTANT:" + str(action_constant)


def fetch_action_constant_number_from_constant_string(action_constant_string):
    action_constant_string = action_constant_string.upper()
    if action_constant_string in 'ACTION_VOTER_GUIDE_VISIT':
        return 1
    if action_constant_string in 'ACTION_VOTER_GUIDE_ENTRY':
        return 2
    if action_constant_string in 'ACTION_ORGANIZATION_FOLLOW':
        return 3
    if action_constant_string in 'ACTION_ORGANIZATION_AUTO_FOLLOW':
        return 4
    if action_constant_string in 'ACTION_ISSUE_FOLLOW':
        return 5
    if action_constant_string in 'ACTION_BALLOT_VISIT':
        return 6
    if action_constant_string in 'ACTION_POSITION_TAKEN':
        return 7
    if action_constant_string in 'ACTION_VOTER_TWITTER_AUTH':
        return 8
    if action_constant_string in 'ACTION_VOTER_FACEBOOK_AUTH':
        return 9
    if action_constant_string in 'ACTION_WELCOME_ENTRY':
        return 10
    if action_constant_string in 'ACTION_FRIEND_ENTRY':
        return 11
    if action_constant_string in 'ACTION_WELCOME_VISIT':
        return 12
    if action_constant_string in 'ACTION_ORGANIZATION_FOLLOW_IGNORE':
        return 13
    if action_constant_string in 'ACTION_ORGANIZATION_STOP_FOLLOWING':
        return 14
    if action_constant_string in 'ACTION_ISSUE_FOLLOW_IGNORE':
        return 15
    if action_constant_string in 'ACTION_ISSUE_STOP_FOLLOWING':
        return 16
    if action_constant_string in 'ACTION_MODAL_ISSUES':
        return 17
    if action_constant_string in 'ACTION_MODAL_ORGANIZATIONS':
        return 18
    if action_constant_string in 'ACTION_MODAL_POSITIONS':
        return 19
    if action_constant_string in 'ACTION_MODAL_FRIENDS':
        return 20
    if action_constant_string in 'ACTION_MODAL_SHARE':
        return 21
    if action_constant_string in 'ACTION_MODAL_VOTE':
        return 22
    if action_constant_string in 'ACTION_NETWORK':
        return 23
    if action_constant_string in 'ACTION_FACEBOOK_INVITABLE_FRIENDS':
        return 24
    if action_constant_string in 'ACTION_DONATE_VISIT':
        return 25
    if action_constant_string in 'ACTION_ACCOUNT_PAGE':
        return 26
    if action_constant_string in 'ACTION_INVITE_BY_EMAIL':
        return 27
    if action_constant_string in 'ACTION_ABOUT_GETTING_STARTED':
        return 28
    if action_constant_string in 'ACTION_ABOUT_VISION':
        return 29
    if action_constant_string in 'ACTION_ABOUT_ORGANIZATION':
        return 30
    if action_constant_string in 'ACTION_ABOUT_TEAM':
        return 31
    if action_constant_string in 'ACTION_ABOUT_MOBILE':
        return 32
    if action_constant_string in 'ACTION_OFFICE':
        return 33
    if action_constant_string in 'ACTION_CANDIDATE':
        return 34
    if action_constant_string in 'ACTION_VOTER_GUIDE_GET_STARTED':
        return 35
    if action_constant_string in 'ACTION_FACEBOOK_AUTHENTICATION_EXISTS':
        return 36
    if action_constant_string in 'ACTION_GOOGLE_AUTHENTICATION_EXISTS':
        return 37
    if action_constant_string in 'ACTION_TWITTER_AUTHENTICATION_EXISTS':
        return 38
    if action_constant_string in 'ACTION_EMAIL_AUTHENTICATION_EXISTS':
        return 39
    if action_constant_string in 'ACTION_ELECTIONS':
        return 40
    if action_constant_string in 'ACTION_ORGANIZATION_STOP_IGNORING':
        return 41
    if action_constant_string in 'ACTION_MODAL_VOTER_PLAN':
        return 42
    if action_constant_string in 'ACTION_READY_VISIT':
        return 43
    if action_constant_string in 'ACTION_SELECT_BALLOT_MODAL':
        return 44
    if action_constant_string in 'ACTION_SHARE_BUTTON_COPY':
        return 45
    if action_constant_string in 'ACTION_SHARE_BUTTON_EMAIL':
        return 46
    if action_constant_string in 'ACTION_SHARE_BUTTON_FACEBOOK':
        return 47
    if action_constant_string in 'ACTION_SHARE_BUTTON_FRIENDS':
        return 48
    if action_constant_string in 'ACTION_SHARE_BUTTON_TWITTER':
        return 49
    if action_constant_string in 'ACTION_SHARE_BALLOT':
        return 50
    if action_constant_string in 'ACTION_SHARE_BALLOT_ALL_OPINIONS':
        return 51
    if action_constant_string in 'ACTION_SHARE_CANDIDATE':
        return 52
    if action_constant_string in 'ACTION_SHARE_CANDIDATE_ALL_OPINIONS':
        return 53
    if action_constant_string in 'ACTION_SHARE_MEASURE':
        return 54
    if action_constant_string in 'ACTION_SHARE_MEASURE_ALL_OPINIONS':
        return 55
    if action_constant_string in 'ACTION_SHARE_OFFICE':
        return 56
    if action_constant_string in 'ACTION_SHARE_OFFICE_ALL_OPINIONS':
        return 57
    if action_constant_string in 'ACTION_SHARE_READY':
        return 58
    if action_constant_string in 'ACTION_SHARE_READY_ALL_OPINIONS':
        return 59
    if action_constant_string in 'ACTION_VIEW_SHARED_BALLOT':
        return 60
    if action_constant_string in 'ACTION_VIEW_SHARED_BALLOT_ALL_OPINIONS':
        return 61
    if action_constant_string in 'ACTION_VIEW_SHARED_CANDIDATE':
        return 62
    if action_constant_string in 'ACTION_VIEW_SHARED_CANDIDATE_ALL_OPINIONS':
        return 63
    if action_constant_string in 'ACTION_VIEW_SHARED_MEASURE':
        return 64
    if action_constant_string in 'ACTION_VIEW_SHARED_MEASURE_ALL_OPINIONS':
        return 65
    if action_constant_string in 'ACTION_VIEW_SHARED_OFFICE':
        return 66
    if action_constant_string in 'ACTION_VIEW_SHARED_OFFICE_ALL_OPINIONS':
        return 67
    if action_constant_string in 'ACTION_VIEW_SHARED_READY':
        return 68
    if action_constant_string in 'ACTION_VIEW_SHARED_READY_ALL_OPINIONS':
        return 69
    if action_constant_string in 'ACTION_SEARCH_OPINIONS':
        return 70
    if action_constant_string in 'ACTION_UNSUBSCRIBE_EMAIL_PAGE':
        return 71
    if action_constant_string in 'ACTION_UNSUBSCRIBE_SMS_PAGE':
        return 72
    if action_constant_string in 'ACTION_MEASURE':
        return 73
    if action_constant_string in 'ACTION_NEWS':
        return 74
    if action_constant_string in 'ACTION_SHARE_ORGANIZATION':
        return 75
    if action_constant_string in 'ACTION_SHARE_ORGANIZATION_ALL_OPINIONS':
        return 76
    if action_constant_string in 'ACTION_VIEW_SHARED_ORGANIZATION':
        return 77
    if action_constant_string in 'ACTION_VIEW_SHARED_ORGANIZATION_ALL_OPINIONS':
        return 78
    return 0
