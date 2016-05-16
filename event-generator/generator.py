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
            print >> self.output_stream, "%% ======== HLA: " + hla.type + " ======== "
            for event in event_list:
                print >> self.output_stream, event.to_etalis()

            print >> self.output_stream, os.linesep


if __name__ == "__main__":
    ## set start of HLAs
    work_start = datetime.datetime.today()
    work_duration = 10  # 10 seocnd duration of working HLA
    work_hla = events.WorkingHLA(person="alex", start_time=work_start, duration=work_duration, lla_step=1, pos_step=1)

    ## set start of UNDEFINED transition HLA at 10 seconds from "working" HLA
    undef_start = work_start + datetime.timedelta(seconds = work_duration)
    undef_duration = 7
    undef_hla = events.UndefinedHLA(person="alex", start_time=undef_start, duration=undef_duration, lla_step=1, pos_step=1)

    ## set preceding HLA
    undef_hla.preceded_by = work_hla


    ## set start of "discussing" HLA - take into account undefined_duration + THE 2 DEFAULT_NON_OVERLAP INTERVALS
    ##  - one for previous "working" HLA  and one for the following "discussing" HLA
    discussing_start = undef_start + datetime.timedelta(seconds = undef_duration + 2 * events.DEFAULT_NON_OVERLAP_DURATION)
    discussing_duration = 10
    discussing_hla = events.DiscussingHLA(person="alex", start_time=discussing_start, duration=discussing_duration, lla_step=1, pos_step=1)

    ## set preceding HLA
    discussing_hla.preceded_by = undef_hla

    ## create desired HLA sequence
    hla_list = [work_hla, undef_hla, discussing_hla]

    ## generate HLA events and print them to file
    with open("generator_out.stream", "w") as outfile:
        gen = Generator(hla_list, outfile)
        gen.generate()

        print "Done. Event stream generated!"