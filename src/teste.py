import os, sys
from datatricks.prompt_commander_flagged import Commander
import datatricks.sped.content as sp
import datatricks.io.file_helper as fh
import sped_handler.sped_definitions as sd
import datatricks.io.file_definitions as fd
import sped_handler.sped_input as ip
import sped_handler.report as rp
import polars as pl



class Sped_cruzamento(Commander):

    def execute(self):
        self.logger.info("Starting application.")
        self.logger.info("Getting files")
        inbound = self.get_incomming_files()
        inbound = fh.get_sped_filters(inbound)
        self.logger.info("Filtering non SPED Files")
        special = self.global_params['special']
        sped_type = rp.get_sped_info(special)
        self.global_params['sped_type'] = sped_type

        df_report = df_report.with_columns(
        pl.when(pl.col(sd.FILE_NAME).is_in(inbound[fd.FILE_NAME]))
            .then(pl.lit('Processado'))
            .otherwise(pl.lit(f'Não Processado'))
            .alias(sd.STATUS))  
        
        df_report = df_report.with_columns(
            pl.when(pl.col(sd.STATUS).eq('Não Processado'))
                    .then(pl.lit(f'O arquivo não é uma {sped_type[sd.TAG_TEMPLATE]}')).alias(sd.REASON))

        try:
            df_sped = sp.read_sped_files(inbound)
        except:
            self.logger.info("There is no file to be processed. Ending execution")
            sys.exit()



if __name__ == "__main__":
    cmd = Sped_cruzamento(app = 'Sped Cruzamento', path=os.path.abspath(__file__), args=sys.argv, flag=1)
    cmd.process()
    config = cmd.global_params
    del(cmd)
    print('acabou a 1a exec')