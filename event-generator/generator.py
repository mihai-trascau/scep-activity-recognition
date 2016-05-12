import datetime
import events
import sys, os

class Generator(object):
    def __init__(self, hla_list, output_stream):
        self.hla_list = hla_list
        self.output_stream = output_stream

    def generate(self):
        for hla in hla_list:
            event_list = hla.generate()
            for event in event_list:
                print >> self.output_stream, event.to_etalis()
                print >> self.output_stream, os.linesep


if __name__ == "__main__":
    work_start = datetime.datetime.today()
    work_duration = 10
    work_hla = events.WorkingHLA(person="alex", start_time=work_start, duration=work_duration, lla_step=1, pos_step=1)

    undef_start = work_start + datetime.timedelta(seconds=10)
    undef_duration = 7
    undef_hla = events.UndefinedHLA(person="alex", start_time=undef_start, duration=undef_duration, lla_step=1, pos_step=1)
    undef_hla.preceded_by = work_hla

    discussing_start = undef_start + datetime.timedelta(seconds = undef_duration + 2 * events.DEFAULT_OVERLAP_DURATION)
    discussing_duration = 10
    discussing_hla = events.DiscussingHLA(person="alex", start_time=discussing_start, duration=discussing_duration, lla_step=1, pos_step=1)
    discussing_hla.preceded_by = undef_hla

    hla_list = [work_hla, undef_hla, discussing_hla]

    gen = Generator(hla_list, sys.stdout)
    gen.generate()