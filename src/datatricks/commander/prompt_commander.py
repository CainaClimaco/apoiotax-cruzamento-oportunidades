import logging
import os
import argparse
import shutil
import zipfile
import glob
import json
from datatricks.commander import commander_definitions
from datatricks.io.file_helper import get_simple_files
from datatricks.io.file_helper import prepare_output_template
from datatricks.io.file_helper import get_all_file_data
from datatricks.io.file_helper import get_sped_filters

class Commander:

    logger = logging.getLogger(__name__)
    global_params = {}
    app_params = {}

    def __init__(self, app, path, args):
        self.app = app
        self.parse_args()
        if self.global_params is None:
            self.global_params = {}
        if self.app_params is None:
            self.app_params = {}
        self.global_params["execution"] = os.path.dirname(path)
        self.global_params["current_script"] = os.path.basename(path)
        self.global_params["output_file_mask_name"] = app + "_{}"
        self.logger = logging.getLogger(__name__)
        self.prepare_logger()
        self.logger.debug("Initializing the Commander for app: {}".
                          format(self.app))

    def load_app_params(self):

        fname = self.global_params["current_script"].split(".")[0] + ".json"
        if os.path.exists(self.global_params["execution"] + os.sep + fname):
            self.logger.debug("Loading app data from file: {}".format(fname))
            with open(self.global_params["execution"] + os.sep + fname, "r") as f:
                self.app_params = json.load(f)

        else:
            self.logger.debug("app file not found : {} Do you need one ?".format(fname))

    def list_params(self):
        self.logger.debug("Listing params")
        for key, value in self.global_params.items():
            print(key, " : ", value)
        print("\n")
        print("=" * 50)
        print("app params_size :" + str(len(self.app_params)), "\n")
        for key, value in self.app_params.items():
            print(key, " : ", value)

    def parse_args(self):
        parser = argparse.ArgumentParser("Basic Parameter processing.")
        parser.add_argument("-i", "--input", help="Input file path", required=True)
        parser.add_argument("-n", "--name", help="project name", required=True)
        parser.add_argument(
            "-s", "--special", help="special script command", required=False
        )
        self.global_params = vars(parser.parse_args())

        self.global_params['special'] = eval(self.global_params['special'])
        for key, value in self.global_params['special'].items():
            self.global_params[f'form_{key}'] = value
        del(self.global_params['special'])

        self.logger.debug(
            "Parsing command line arguments {}".format(self.global_params)
        )
        if not self.validate_params():
            self.logger.error(
                "Invalid input/outputh parameters {}".format(
                    self.global_params["input"]
                ) 
            )
            raise ValueError("Invalid input/outputh parameters")

    def validate_params(self):
        self.logger.debug("Validating path: {}".format(self.global_params["input"]))
        for key, value in self.global_params.items():
            if key == "input" or key == "output":
                if not os.path.exists(value):
                    self.logger.debug("Invalid path: {}".format(value))
                    return False
        return True

    def find_zip_files(self):
        # Use glob to find all zip files in the path
        zip_files = glob.glob(os.path.join(self.global_params["input"], "*.zip"))
        self.logger.debug("Found zip files: {}".format(zip_files))
        if len(zip_files) > 1 or len(zip_files) == 0:
            self.logger.debug("Too many or no zip files found: {}".format(zip_files))
            raise ValueError("Too many or no zip files found: {}".format(zip_files))
        self.global_params["zipfile"] = zip_files[0]

    def create_path(self, directory=None, is_temp=False):
        self.logger.debug(
            "Creating temp path at: {}".format(self.global_params["input"])
        )
        input_path = self.global_params["input"]
        if input_path[-1] == os.sep:
            input_path = input_path + directory
        else:
            input_path = input_path + os.sep + directory

        if os.path.exists(input_path):
            self.logger.debug("Output path already exists: {}".format(input_path))
        else:
            self.logger.debug(
                "Output path do not exists creating it at : {}".format(input_path)
            )
            os.makedirs(input_path, exist_ok=True)

        if is_temp:
            self.global_params["temp"] = input_path + os.sep
        else:
            self.global_params["output"] = input_path + os.sep

    def unzip_file(self):
        self.logger.debug("Unzipping file: {}".format(self.global_params["zipfile"]))
        with zipfile.ZipFile(self.global_params["zipfile"], "r") as zip_ref:
            zip_ref.extractall(self.global_params["temp"])

    def zip_files(self, working_dir=None):

        with zipfile.ZipFile(
            self.global_params["output"] + commander_definitions.OUTPUT_FILE_NAME, "w"
        ) as zipf:
            for file in os.listdir(working_dir):
                if file.split(".")[-1] != "zip":
                    file_path = os.path.join(working_dir, file)
                    if os.path.isfile(file_path):
                        zipf.write(file_path, arcname=os.path.basename(file_path))

    def clean_temp_path(self):
        self.logger.debug("Cleaning temp path: {}".format(self.global_params["temp"]))
        if commander_definitions.TEMP_DIR_NAME not in str(self.global_params["temp"]):
            raise ValueError(
                "Invalid temp path:{}  temp folders are removed".format(
                    str(self.global_params["temp"])
                )
            )
        shutil.rmtree(self.global_params["temp"])

    def start(self):
        self.logger.debug("Starting the app: {}".format(self.app))
        self.find_zip_files()
        self.create_path(directory=commander_definitions.TEMP_DIR_NAME, is_temp=True)
        self.create_path(directory=commander_definitions.OUTPUT_DIR_NAME, is_temp=False)
        self.get_template_path()
        self.get_assets_path()
        self.logger.debug(
            "using template path: {}".format(self.global_params["template_path"])
        )
        self.prepare_templates()
        self.logger.debug(
            "using template files: {}".format(self.global_params["template_files"])
        )
        self.unzip_file()
        self.logger.debug(
            "{} app initialized... Calling next method on the chain".format(self.app)
        )

    def process(self):
        self.logger.debug("Processing the app: {}".format(self.app))
        self.load_app_params()
        try:
            self.start()
            self.execute()
        except Exception as e:
            self.logger.error("Error processing the app: {}".format(self.app))
            self.write_error_file(self.global_params["input"], str(e))
            raise e
        finally:
            self.logger.info("Done processing the app: {}".format(self.app))
            self.logger.debug(
                "Zipping output files: {}".format(self.global_params["output"])
            )
            self.zip_files(working_dir=self.global_params["output"])
            self.clean_temp_path()
            self.write_Ok_file(self.global_params["input"])

    
    def write_Ok_file(self, path):
        if not os.path.exists(path + os.sep + commander_definitions.ERROR_FILE_NAME):
            with open(path + os.sep + commander_definitions.OK_FILE_NAME, "w") as f:
                f.write("OK")

    def write_error_file(self, path, error):
        with open(path + os.sep + commander_definitions.ERROR_FILE_NAME, "w") as f:
            f.write(error)

    
    def execute(self):
        self.logger.debug("Executing the app: {}".format(self.app))
        pass

    def get_incomming_files(self):
        self.logger.debug("Getting incomming files")
        return get_all_file_data(self.global_params["temp"])
    
    def add_sped_filters(self, df):
        return get_sped_filters(df)

    def get_template_path(self):
        if os.path.exists(
            self.global_params["execution"] + os.sep + commander_definitions.TEMPLATE_DIR_NAME
        ):
            logging.debug(
                "Template path found: {}".format(
                    self.global_params["execution"]
                    + os.sep
                    + commander_definitions.TEMPLATE_DIR_NAME
                )
            )
            self.global_params["template_path"] = (
                self.global_params["execution"] + os.sep + commander_definitions.TEMPLATE_DIR_NAME
            )
        else:
            logging.error(
                "Template path not found: {}".format(
                    self.global_params["execution"]
                    + os.sep
                    + commander_definitions.TEMPLATE_DIR_NAME
                )
            )
            raise ValueError(
                "Template path not found: {}".format(
                    self.global_params["execution"]
                    + os.sep
                    + commander_definitions.TEMPLATE_DIR_NAME
                )
            )

    def get_assets_path(self):
        if os.path.exists(
            self.global_params["execution"] + os.sep + commander_definitions.ASSETS_DIR_NAME
        ):
            logging.debug(
                "assets path found: {}".format(
                    self.global_params["execution"]
                    + os.sep
                    + commander_definitions.ASSETS_DIR_NAME
                )
            )
            self.global_params["asset_path"] = (
                self.global_params["execution"] + os.sep + commander_definitions.ASSETS_DIR_NAME
            )
        else:
            logging.error(
                "Asset path not found: {}".format(
                    self.global_params["execution"]
                    + os.sep
                    + commander_definitions.ASSETS_DIR_NAME
                )
            )
            self.global_params["asset_path"] = None

    def get_template_files(self):
        logging.debug("Getting template files")
        return get_simple_files(self.global_params["template_path"])

    def get_assets_files(self):
        logging.debug("Getting assets files")
        if self.global_params["asset_path"] is None:
            raise ValueError("No asset path found")

        return get_simple_files(self.global_params["asset_path"])

    def prepare_templates(self):
        logging.debug("Moving template files")
        resp = []
        f_idx = 1
        for file in self.get_template_files():
            resp.append(
                prepare_output_template(
                    template_path=file,
                    output_path=self.global_params["output"],
                    project_name=self.global_params["output_file_mask_name"].format(
                        self.global_params["name"] + "_" + str(f_idx)
                    )
                )
            )
            f_idx += 1
            
        self.global_params["template_files"] = resp

    def prepare_logger(self):
        self.logger.setLevel(logging.DEBUG)
        handler = logging.FileHandler("prompt_commander.log")
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
