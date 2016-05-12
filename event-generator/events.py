import datetime, random
import numpy as np

from scipy.stats import rv_discrete
from utils import GaussianPosTransition

DEFAULT_DURATION         = 10
DEFAULT_OVERLAP_DURATION = 2

DEFAULT_UPDATE_STEP = 1
DEFAULT_DELTA_STEP  = 1

DEFAULT_TP_MU       = 0.85
DEFAULT_TP_SIGMA    = 0.2

DEFAULT_FP_MU       = 0.35
DEFAULT_FP_SIGMA    = 0.15


DEFAULT_PERSON = "doe"

class AtomicEvent(object):
    def __init__(self, timestamp = None, certainty = 1.0, person=DEFAULT_PERSON):
        self.certainty = certainty
        if timestamp is None:
            self.timestamp = datetime.datetime.today()
        else:
            self.timestamp = timestamp

        self.person = person


    @staticmethod
    def get_tp_certainty_value(mu, sigma):
        # generate certainty from normal distribution: lower cap at 0.65, upper cap at 1.0
        if mu < 0.65 or mu > 1:
            return 0.85

        val = np.random.normal(mu, sigma)
        if val < 0.65:
            val = 0.65
        elif val > 1.0:
            val = 1.0

        return val

    @staticmethod
    def get_fp_certainty_value(mu, sigma):
        # generate certainty from normal distribution: lower cap at 0.2, upper cap at 0.5
        if mu < 0.2 or mu > 0.5:
            return 0.35

        val = np.random.normal(mu, sigma)
        if val < 0.2:
            val = 0.2
        elif val > 0.5:
            val = 0.5

        return val

    @staticmethod
    def to_datime(timestamp):
        return "datime" + "(" \
                + timestamp.year + ", " \
                + timestamp.month + ", " \
                + timestamp.day + ", " \
                + timestamp.hour + ", " \
                + timestamp.minute + ", " \
                + timestamp.second + ", " \
                + "1" \
                + ")"

    def meta_to_etalis(self):
        etalis_form = "meta"
        etalis_form += "("
        etalis_form += str((self.timestamp - datetime.datetime(1970,1,1)).total_seconds())
        etalis_form += ", "

        etalis_form += str(self.certainty)
        etalis_form += ")"

        return etalis_form


    def predicate_to_etalis(self):
        return None

    def to_etalis(self):
        etalis_form = "event"
        etalis_form += "("

        etalis_form += self.predicate_to_etalis()
        etalis_form += ", "

        etalis_form += "["
        etalis_form += AtomicEvent.to_datime(self.timestamp)
        etalis_form += ", "
        etalis_form += AtomicEvent.to_datime(self.timestamp)
        etalis_form += "]"
        etalis_form += ")"
        etalis_form += "."

        return etalis_form



class LLA(AtomicEvent):
    WALKING     = "walking"
    SITTING     = "sitting"
    STANDING    = "standing"

    LLA_ADJACENCY = {
        WALKING:    [STANDING],
        STANDING:   [WALKING]
    }

    def __init__(self, type = None, person = DEFAULT_PERSON, timestamp = None, certainty = 1.0):
        super(LLA, self).__init__(timestamp=timestamp, certainty=certainty, person=person)
        self.type = type


    def predicate_to_etalis(self):
        etalis_form = "lla"
        etalis_form += "("
        etalis_form += self.person
        etalis_form += ", "

        etalis_form += str(self.type)
        etalis_form += ", "

        etalis_form += self.meta_to_etalis()
        etalis_form += ")"

        return etalis_form



class Position(AtomicEvent):
    WORK_AREA           = "work_area"
    CONFERENCE_AREA     = "conference_area"
    ENTERTAINMENT_AREA  = "entertainment_area"
    DINING_AREA         = "dining_area"
    SNACK_AREA          = "snack_area"
    EXERCISE_AREA       = "exercise_area"
    HYGENE_AREA         = "hygene_area"

    AREA_ADJACENCY = {
        WORK_AREA:          [DINING_AREA],
        CONFERENCE_AREA:    [DINING_AREA, ENTERTAINMENT_AREA],
        ENTERTAINMENT_AREA: [CONFERENCE_AREA, EXERCISE_AREA],
        DINING_AREA:        [WORK_AREA, CONFERENCE_AREA],
        SNACK_AREA:         [EXERCISE_AREA, HYGENE_AREA],
        EXERCISE_AREA:      [ENTERTAINMENT_AREA, SNACK_AREA],
        HYGENE_AREA:        [SNACK_AREA, WORK_AREA]
    }

    def __init__(self, type = None, person = DEFAULT_PERSON, timestamp = None, certainty = 1.0):
        super(Position, self).__init__(timestamp=timestamp, certainty=certainty, person=person)
        self.type = type


    def predicate_to_etalis(self):
        etalis_form = "pos"
        etalis_form += "("
        etalis_form += self.person
        etalis_form += ", "

        etalis_form += str(self.type)
        etalis_form += ", "

        etalis_form += self.meta_to_etalis()
        etalis_form += ")"

        return etalis_form




class HLA(object):
    WORKING             = "working"
    DISCUSSING          = "discussing"

    ENTERTAINMENT       = "entertainment"
    DINING              = "dining"
    SNACKING            = "snacking"
    EXERCISING          = "exercising"
    HYGENE              = "hygene"
    UNDEFINED           = "undefined"


    def __init__(self, type = UNDEFINED, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP,
                 accepted_combinations = None):

        self.type = type
        self.person = person

        self.start_time = start_time
        self.duration = duration
        self.lla_step = lla_step
        self.pos_step = pos_step

        ## HLAs that preced and follow the current one
        self._followed_by = None
        self._preceded_by = None

        ## HLA generation flags
        self.complex_transition = False

        self.lla_error_rate = 0
        self.pos_error_rate = 0

        self.lla_false_detect_rate = 0
        self.pos_false_detect_rate = 0

        ## list of accepted LLAs position compositions and the accepted position
        self.accepted_combinations = accepted_combinations

        ## the actual chosen position and LLA combination that activates this HLA
        self.active_pos = None
        self.active_lla = None

    @property
    def followed_by(self):
        return self._followed_by

    @followed_by.setter
    def followed_by(self, hla):
        self._followed_by = hla
        hla.preceded_by = self

    @property
    def preceded_by(self):
        return self._preceded_by

    @preceded_by.setter
    def preceded_by(self, hla):
        self._preceded_by = hla
        hla.followed_by = self


    @staticmethod
    def generate_overlap_transition(pos_type, lla_type, current_ts, overlap_duration, pos_step, lla_step, person):
        event_list = []

        ts_pos = ts_lla = current_ts
        computed_duration = 0

        while computed_duration <= overlap_duration:
            ts_limit = current_ts + datetime.timedelta(seconds=DEFAULT_DELTA_STEP)
            while (ts_pos <= ts_limit or ts_lla <= ts_limit):
                if ts_pos <= ts_limit:
                    cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                    pos = Position(type=pos_type, person=person, timestamp=ts_pos, certainty=cert)
                    event_list.append(pos)

                ts_pos = ts_pos + datetime.timedelta(seconds=pos_step)

                if ts_lla <= ts_limit:
                    cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                    lla = LLA(type=lla_type, person=person, timestamp=ts_lla, certainty=cert)
                    event_list.append(lla)

                ts_lla = ts_lla + datetime.timedelta(seconds=lla_step)

            current_ts = ts_limit
            computed_duration += DEFAULT_DELTA_STEP

        return event_list, current_ts


    @staticmethod
    def generate_simple_rampdown_transition(pos_type, lla_type, start_time, duration, pos_step, lla_step, person):
        aux_events = []

        end_time = start_time + datetime.timedelta(seconds=duration)

        pos_metas = GaussianPosTransition(start_time=start_time, end_time=end_time,
                                               delta=pos_step, max_value=DEFAULT_TP_MU, right_only=True)

        # generate Position events according to their step and add them to the aux list
        for meta in pos_metas:
            pos = Position(type=pos_type, person=person,
                           timestamp=meta['timestamp'], certainty=meta['certainty'])
            aux_events.append(pos)

        # generate LLA events according to their step and add them to the aux list
        computed_duration = 0
        current_ts = start_time

        while computed_duration <= duration:
            ts_limit = current_ts + datetime.timedelta(seconds=DEFAULT_DELTA_STEP)
            while ts_lla <= ts_limit:
                cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                lla = LLA(type=lla_type, person=person, timestamp=ts_lla, certainty=cert)
                aux_events.append(lla)
                ts_lla = ts_lla + datetime.timedelta(seconds=lla_step)

            current_ts = ts_limit
            computed_duration += DEFAULT_DELTA_STEP

        # order aux_events by timestamp and then add to overall event list
        aux_events.sort(key=lambda ev: ev.timestamp)

        return aux_events


    @staticmethod
    def generate_simple_rampup_transition(pos_type, lla_type, start_time, duration, pos_step, lla_step, person):
        aux_events = []

        end_time = start_time + datetime.timedelta(seconds=duration)

        pos_metas = GaussianPosTransition(start_time=start_time, end_time=end_time,
                                               delta=pos_step, max_value=DEFAULT_TP_MU, left_only=True)

        # generate Position events according to their step and add them to the aux list
        for meta in pos_metas:
            pos = Position(type=pos_type, person=person,
                           timestamp=meta['timestamp'], certainty=meta['certainty'])
            aux_events.append(pos)

        # generate LLA events according to their step and add them to the aux list
        computed_duration = 0
        current_ts = start_time

        while computed_duration <= duration:
            ts_limit = current_ts + datetime.timedelta(seconds=DEFAULT_DELTA_STEP)
            while ts_lla <= ts_limit:
                cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                lla = LLA(type=lla_type, person=person, timestamp=ts_lla, certainty=cert)
                aux_events.append(lla)
                ts_lla = ts_lla + datetime.timedelta(seconds=lla_step)

            current_ts = ts_limit
            computed_duration += DEFAULT_DELTA_STEP

        # order aux_events by timestamp and then add to overall event list
        aux_events.sort(key=lambda ev: ev.timestamp)

        return aux_events, end_time



    def generate(self, with_sleep = False):
        event_list = []

        pos_error_distrib = rv_discrete(values=([True, False], [self.pos_error_rate, 1 - self.pos_error_rate]))
        lla_error_distrib = rv_discrete(values=([True, False], [self.lla_error_rate, 1 - self.lla_error_rate]))

        pos_fd_distrib = rv_discrete(values=([True, False], [self.pos_false_detect_rate, 1 - self.pos_false_detect_rate]))
        lla_fd_distrib = rv_discrete(values=([True, False], [self.lla_false_detect_rate, 1 - self.lla_false_detect_rate]))

        if not with_sleep:
            if self.type == HLA.UNDEFINED:
                if self.complex_transition:
                    raise NotImplementedError("Complex HLA Transitions not implemented yet!")
                else:
                    ''' In this case we only generate the WALKING LLA and alter the start and end positions according to the previous and next HLAs'''
                    transition_start = self.start_time

                    prev_pos = next_pos = None
                    if self._preceded_by:
                        prev_pos = self._preceded_by.active_pos

                    if self._followed_by:
                        next_pos = self._followed_by.active_pos

                    if prev_pos:
                        ## generate overlap events
                        aux_overlap_events, transition_start = HLA.generate_overlap_transition(prev_pos, LLA.WALKING, transition_start, DEFAULT_OVERLAP_DURATION, self.pos_step, self.lla_step, self.person)

                        ## generate rampdown GaussionPosTransition for duration of UNDEFINED event ////////
                        aux_rampdown_events = HLA.generate_simple_rampdown_transition(prev_pos, LLA.WALKING, transition_start, self.duration, self.pos_step, self.lla_step, self.person)

                        event_list.extend(aux_overlap_events)
                        event_list.extend(aux_rampdown_events)

                    if next_pos:
                        ## generate rampup events
                        aux_rampup_events, transition_start = HLA.generate_simple_rampup_transition(next_pos, LLA.WALKING, transition_start, self.duration, self.pos_step, self.lla_step, self.person)

                        ## generate overlap events
                        aux_overlap_events, transition_end = HLA.generate_overlap_transition(next_pos, LLA.WALKING, transition_start, DEFAULT_OVERLAP_DURATION, self.pos_step, self.lla_step, self.person)

                        event_list.extend(aux_rampup_events)
                        event_list.extend(aux_overlap_events)

            else:
                if self.accepted_combinations:
                    comb_idx = random.randint(0, len(self.accepted_combinations) - 1)
                    self.active_pos = self.accepted_combinations[comb_idx]['position']
                    self.active_lla = self.accepted_combinations[comb_idx]['lla']

                    computed_duration = 0
                    ts_pos = ts_lla = current_ts = self.start_time

                    while True:
                        if computed_duration <= self.duration:
                            ts_limit = current_ts + datetime.timedelta(seconds=DEFAULT_DELTA_STEP)

                            while (ts_pos <= ts_limit or ts_lla <= ts_limit):
                                ''' ======== Generate position event if possible ======== '''
                                if ts_pos <= ts_limit:
                                    pos_error = pos_error_distrib.rvs()
                                    pos_fd = pos_fd_distrib.rvs()

                                    if not pos_error:
                                        cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                                        pos = Position(type=self.active_pos, person = self.person, timestamp=ts_pos, certainty=cert)
                                        event_list.append(pos)
                                    else:
                                        cert = AtomicEvent.get_fp_certainty_value(DEFAULT_FP_MU, DEFAULT_FP_SIGMA)
                                        pos = Position(type=self.active_pos, person=self.person, timestamp=ts_pos, certainty=cert)
                                        event_list.append(pos)

                                        if pos_fd:
                                            false_pos_types = Position.AREA_ADJACENCY.get(self.active_pos)
                                            if false_pos_types:
                                                idx = random.randint(0, len(false_pos_types) - 1)
                                                false_pos_type = false_pos_types[idx]

                                                cert = AtomicEvent.get_fp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                                                pos = Position(type=false_pos_type, person=self.person, timestamp=ts_pos, certainty=cert)
                                                event_list.append(pos)

                                ts_pos = ts_pos + datetime.timedelta(seconds=self.pos_step)


                                ''' ======== Generate LLA event if possible ======== '''
                                if ts_lla <= ts_limit:
                                    lla_error = lla_error_distrib.rvs()
                                    lla_fd = lla_fd_distrib.rvs()

                                    if not lla_error:
                                        cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                                        lla = LLA(type=self.active_lla, person=self.person, timestamp=ts_lla, certainty=cert)
                                        event_list.append(lla)
                                    else:
                                        cert = AtomicEvent.get_tp_certainty_value(DEFAULT_FP_MU, DEFAULT_FP_SIGMA)
                                        lla = LLA(type=self.active_lla, person=self.person, timestamp=ts_lla, certainty=cert)
                                        event_list.append(lla)

                                        if lla_fd:
                                            false_llas = LLA.LLA_ADJACENCY.get(self.active_lla)
                                            if false_llas:
                                                idx = random.randint(0, len(false_llas) - 1)
                                                false_lla_type = false_llas[idx]

                                                cert = AtomicEvent.get_tp_certainty_value(DEFAULT_TP_MU, DEFAULT_TP_SIGMA)
                                                lla = LLA(type=false_lla_type, person=self.person, timestamp=ts_lla, certainty=cert)
                                                event_list.append(lla)

                                    ts_lla = ts_lla + datetime.timedelta(seconds=self.lla_step)


                            current_ts = ts_limit
                            computed_duration += DEFAULT_DELTA_STEP
                        else:
                            break

                else:
                    raise ValueError("No accepted LLA-position combinations for non-undefined HLA!!!")

            return event_list
        else:
            raise NotImplementedError("HLA generation with sleep statements between events not implemented!")



"""====================================================================================================================="""
"""=================================================== SPECIFIC HLAs ==================================================="""
"""====================================================================================================================="""

class WorkingHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(WorkingHLA, self).__init__(type=HLA.WORKING, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.SITTING, "position": Position.WORK_AREA}])


class DiscussingHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(DiscussingHLA, self).__init__(type=HLA.DISCUSSING, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations=[{"lla": LLA.SITTING, "position": Position.CONFERENCE_AREA},
                                                                {"lla": LLA.STANDING, "position": Position.CONFERENCE_AREA}
                                                                ])


class DiningHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(DiningHLA, self).__init__(type=HLA.DINING, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.SITTING, "position": Position.DINING_AREA}])


class SnackingHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(SnackingHLA, self).__init__(type=HLA.SNACKING, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.STANDING, "position": Position.DINING_AREA}])


class EntertainmentHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(EntertainmentHLA, self).__init__(type=HLA.ENTERTAINMENT, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.SITTING,  "position": Position.ENTERTAINMENT_AREA},
                                                                  {"lla": LLA.STANDING, "position": Position.ENTERTAINMENT_AREA}])


class ExerciseHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(ExerciseHLA, self).__init__(type=HLA.EXERCISING, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.STANDING, "position": Position.EXERCISE_AREA}])



class HygeneHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP):

        super(HygeneHLA, self).__init__(type=HLA.HYGENE, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step,
                                         accepted_combinations = [{"lla": LLA.STANDING, "position": Position.HYGENE_AREA},
                                                                  {"lla": LLA.WALKING,  "position": Position.HYGENE_AREA}])



class UndefinedHLA(HLA):
    def __init__(self, person = DEFAULT_PERSON,
                 start_time = datetime.datetime.today(), duration = DEFAULT_DURATION,
                 lla_step = DEFAULT_UPDATE_STEP, pos_step = DEFAULT_UPDATE_STEP,
                 direct_transition = True, complex_transition = False):

        super(UndefinedHLA, self).__init__(type=HLA.UNDEFINED, person=person,
                                         start_time=start_time, duration=duration,
                                         lla_step=lla_step, pos_step=pos_step)
        self.direct_transition = direct_transition
        self.complex_transition = complex_transition