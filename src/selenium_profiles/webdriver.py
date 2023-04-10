# noinspection PyUnresolvedReferences
from selenium.webdriver import ChromeOptions
import warnings


#
class Chrome:
    # noinspection PyUnusedLocal,PyDefaultArgument
    def __init__(self, profile: dict = None, chrome_binary:str=None, executable_path:str = None,
                 options = None,dublicate_policy: str = "warn-add", safe_dublicates: list = ["--add-extension"],
                 uc_driver: bool = False):
        self.cdp = None
        self.started = None
        from collections import defaultdict
        from selenium.webdriver.chrome.service import Service as ChromeService
        from selenium_profiles.utils.colab_utils import is_colab
        from selenium_profiles.scripts.cdp_tools import cdp_tools
        from selenium_profiles.scripts.profiles import options as options_handler
        from selenium_profiles.utils.utils import valid_key


        # initial attributes
        self.uc_driver = uc_driver
        self.executable_path = executable_path
        self.cdp_tools = cdp_tools


        valid_key(profile.keys(), ["cdp", "options"], "profile (selenium-profiles)")
        self.profile = defaultdict(lambda: None)
        self.profile.update(profile)

        # sandbox handling for google-colab
        if is_colab():
            # todo: nested default-dict with Lambda: None
            if self.profile["options"]:
                # noinspection PyUnresolvedReferences
                if 'sandbox' in self.profile["options"].keys():
                    # noinspection PyUnresolvedReferences
                    if self.profile["options"]["sandbox"] is True:
                        import warnings
                        warnings.warn('Google-colab doesn\'t work with sandbox enabled yet, disabling sandbox')
                else:
                     # noinspection PyUnresolvedReferences
                     self.profile["options"].update({"sandbox": False})
            else:
                # noinspection PyTypeChecker
                self.profile.update({"options": {"sandbox": False}})

        # default chrome_options

        if uc_driver:
           import undetected_chromedriver as uc  # undetected chromedriver
           self.driver = uc.Chrome
           if not options:
               options = uc.ChromeOptions()  # selenium.webdriver options, https://peter.sh/experiments/chromium-command-line-switches/$
        else:
            from selenium import webdriver
            self.driver = webdriver.Chrome

        if not options:
            from selenium import webdriver
            options = webdriver.ChromeOptions()

        # options-manager
        self.options = options_handler(options, self.profile["options"], dublicate_policy=dublicate_policy, safe_dublicates=safe_dublicates)

        # executable-path for chromedriver
        if executable_path is None:  # chromedriver path
            if not uc_driver:
                from selenium.webdriver.chrome.service import DEFAULT_EXECUTABLE_PATH
                executable_path = DEFAULT_EXECUTABLE_PATH

        self.service = ChromeService(executable_path=executable_path)

        # chrome executable path
        if not (chrome_binary is None):
            # noinspection PyUnresolvedReferences
            self.options.Options.binary_location = chrome_binary

    def start(self):
        from selenium_profiles.scripts import undetected

        if self.started:
            raise TypeError("webdriver.Chrome() object can't be re-used")

        if self.uc_driver:
            # noinspection PyUnboundLocalVariable
            self.driver = self.driver(use_subprocess=True, options=self.options.Options, keep_alive=True,
                                      driver_executable_path=self.executable_path)  # start undetected_chromedriver
            self.started = True
        else:

            # is adb used ?
            try:
                # noinspection PyUnresolvedReferences
                adb = self.profile["options"]["adb"]
            except TypeError:
                adb = None
            except KeyError:
                adb = None


            # undetected-options
            self.options.Options = undetected.config_options(self.options.Options, adb=adb)

            # Actual start of chrome
            self.driver = self.driver(options=self.options.Options, service=self.service)  # start selenium webdriver
            self.started = True

        self.driver.get("http://lumtest.com/myip.json")  # wait browser to start

        self.cdp_tools = self.cdp_tools(self.driver)

        self.cdp_tools.evaluate_on_document_identifiers.update({1: # we know that it is there:)
                """(function () {window.cdc_adoQpoasnfa76pfcZLmcfl_Array = window.Array;
                window.cdc_adoQpoasnfa76pfcZLmcfl_Object = window.Object;
                window.cdc_adoQpoasnfa76pfcZLmcfl_Promise = window.Promise;
                window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy = window.Proxy;
                window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol = window.Symbol;
                }) ();"""})

        # execute cdp based on profile
        # noinspection PyAttributeOutsideInit
        from selenium_profiles.scripts.profiles import cdp as cdp_handler
        self.cdp = cdp_handler(self.driver, self.cdp_tools)
        self.cdp.apply(cdp_profile=self.profile["cdp"])

        if not self.uc_driver:
            undetected.exec_cdp(self.driver, self.cdp_tools)


        self.add_funcs_to_driver()

        # Return actual driver
        return self.driver

    def add_funcs_to_driver(self):

        class utils(object):
            pass
            def apply(self, profile:dict):
                from selenium_profiles.utils.utils import valid_key
                valid_key(profile.keys(),["cdp", "options"], "profile (selenium-profiles)")
                if "options" in profile.keys():
                    warnings.warn('profile["options"] can\'t be applied when driver allready started')
                if "cdp" in profile.keys():
                    # noinspection PyUnresolvedReferences
                    self.cdp.apply(profile)

        utils = utils()

        # our profile
        utils.__setattr__("profile",self.profile)

        # add selenium-interceptor
        from selenium_interceptor.interceptor import cdp_listener
        utils.__setattr__("cdp_listener", cdp_listener(driver=self.driver))

        # add my functions
        utils.__setattr__("get_profile", self.get_profile)
        utils.__setattr__("export_profile", self.export_profile)
        utils.__setattr__("get_profile", self.get_profile)
        utils.__setattr__("cdp", self.cdp)

        from selenium_profiles.scripts.driver_utils import requests, actions, TouchActionChain

        # requests.fetch
        requests = requests(self.driver)
        utils.__setattr__("fetch", requests.fetch)

        actions = actions(self.driver)
        actions.__setattr__("TouchActionChain", TouchActionChain)
        utils.__setattr__("actions", actions)

        # patch cookie functions
        self.driver.get_cookies = self.cdp_tools.get_cookies
        self.driver.add_cookie = self.cdp_tools.add_cookie
        self.driver.get_cookie = self.cdp_tools.get_cookie
        self.driver.delete_cookie = self.cdp_tools.delete_cookie
        self.driver.delete_all_cookies = self.cdp_tools.delete_all_cookies

        self.driver.profiles = utils

    def export_profile(self, to_path=None):
        import shutil
        self.ensure_started()

        if not to_path: # default path
            from selenium_profiles.utils.utils import sel_profiles_path
            to_path = sel_profiles_path() + "files/user_dir"


        # noinspection PyUnresolvedReferences
        shutil.copytree(self.driver.user_data_dir, to_path)

    def get_profile(self):
        from selenium_profiles.utils.utils import read
        self.ensure_started()

        js = read('js/export_profile.js', sel_root=True)

        # noinspection PyArgumentList
        return self.driver.execute_async_script(js)

    def ensure_started(self):
        if not self.started:
            raise TypeError("driver needs to be started first :)")
