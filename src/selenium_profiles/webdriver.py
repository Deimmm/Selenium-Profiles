import warnings
from collections import defaultdict
from selenium_profiles.utils.utils import valid_key
import typing

from selenium.webdriver.chrome.service import Service as ChromeService

from selenium_profiles.utils.colab_utils import is_colab
from selenium_profiles.scripts.profiles import options as options_handler

from selenium.webdriver import Chrome as BaseDriver
class Chrome(BaseDriver):

    # noinspection PyDefaultArgument
    def __init__(self, profile: dict = None, chrome_binary: str = None, executable_path: str = None,
                 options=None, duplicate_policy: str = "warn-add", safe_duplicates: list = ["--add-extension"],
                 base_drivers:tuple=None,
                 uc_driver: bool or None = None, seleniumwire_options: dict or bool or None = None, injector_options:dict or bool or None = None,
                 **kwargs):

        import seleniumwire.undetected_chromedriver as wire_uc_webdriver
        import undetected_chromedriver as uc_webdriver
        from seleniumwire import webdriver as wire_webdriver

        if not base_drivers:
            base_drivers = tuple()

        # import webdriver
        webdriver = None
        if uc_driver:
            if seleniumwire_options:
                webdriver = wire_uc_webdriver
            else:
                webdriver = uc_webdriver
        else:
            if seleniumwire_options:
                webdriver = wire_webdriver

        if webdriver:
            base_drivers = (webdriver.Chrome,) + base_drivers

        if not options:
            if webdriver:
                options = webdriver.ChromeOptions()
            else:
                from selenium.webdriver import ChromeOptions
                options = ChromeOptions()

        if len(base_drivers) > 1:
            warnings.warn("More than one base_driver might not initialize correctly, seems buggy.\n Also, you might try different order")
        if (len(base_drivers) == 1) and (base_drivers[0] == Chrome.__base__):
            pass # got selenium.webdriver.Chrome as BaseDriver
        elif not base_drivers:
            pass
        else :
            Chrome.__bases__ = base_drivers

        if not profile:
            profile = {}

        valid_key(profile.keys(), ["cdp", "options"], "profile (selenium-profiles)")

        if type(seleniumwire_options) is dict:
            kwargs.update({"seleniumwire_options": seleniumwire_options})
        elif not (type(seleniumwire_options) is bool or seleniumwire_options is None):
            raise ValueError("Expected NoneType, dict or bool")

        defdict = defaultdict(lambda: None)
        defdict.update(profile)
        profile = defdict

        # sandbox handling for google-colab
        if is_colab():
            # todo: nested default-dict with Lambda: None
            if profile["options"]:
                # noinspection PyUnresolvedReferences
                if 'sandbox' in profile["options"].keys():
                    # noinspection PyUnresolvedReferences
                    if profile["options"]["sandbox"] is True:
                        warnings.warn('Google-colab doesn\'t work with sandbox enabled yet, disabling sandbox')
                else:
                    # noinspection PyUnresolvedReferences
                    profile["options"].update({"sandbox": False})
            else:
                # noinspection PyTypeChecker
                profile.update({"options": {"sandbox": False}})

        # options-manager
        options_manager = options_handler(options, profile["options"], duplicate_policy=duplicate_policy,
                                          safe_duplicates=safe_duplicates)

        # chrome executable path
        if not chrome_binary:
            options_manager.Options.binary_location = chrome_binary

        if (uc_webdriver.Chrome in base_drivers) or (wire_uc_webdriver.Chrome in base_drivers):
            if executable_path:
                kwargs.update({"driver_executable_path": executable_path})
        else:
            # detectability options
            from selenium_profiles.scripts import undetected

            # is adb used ?
            try:
                # noinspection PyUnresolvedReferences
                adb = profile["options"]["adb"]
            except TypeError:
                adb = None
            except KeyError:
                adb = None

            options_manager.Options = undetected.config_options(options_manager.Options, adb=adb)

            # chromedriver path
            if executable_path:
                kwargs.update({"service": ChromeService(executable_path=executable_path)})

        if injector_options:
            from selenium_injector.scripts.driverless import Driverless
            if (injector_options is True) or injector_options == {}:
                injector_options = {}
            driverless = Driverless(**injector_options)

            options_manager.add_argument(f'--load-extension={driverless.path}')

        # add options to kwargs
        kwargs.update({"options": options_manager.Options})

        # Actual start of chrome
        super().__init__(**kwargs)
        # cdp tools

        self.get("chrome://version/")  # wait browser to start

        self.profiles = profiles(self, profile)


        self.profiles.cdp_handler.evaluate_on_document_identifiers.update({1:  # we know that it is there:)
                                                                """(function () {window.cdc_adoQpoasnfa76pfcZLmcfl_Array = window.Array;
                                                                window.cdc_adoQpoasnfa76pfcZLmcfl_Object = window.Object;
                                                                window.cdc_adoQpoasnfa76pfcZLmcfl_Promise = window.Promise;
                                                                window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy = window.Proxy;
                                                                window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol = window.Symbol;
                                                                }) ();"""})

        self.profiles.cdp_handler.apply(cdp_profile=profile["cdp"])

        if not uc_driver:
            from selenium_profiles.scripts import undetected
            undetected.exec_cdp(self, cdp_handler=self.profiles.cdp_handler)

        if injector_options or injector_options == {}:
            # noinspection PyUnboundLocalVariable
            self.profiles.driverless = driverless

            # connection to tab-0
            tab_index = self.window_handles.index(self.current_window_handle).__str__()
            self.profiles.driverless.tab_user = "tab-" + tab_index
            config = f"""
                            var connection = new connector("{self.profiles.driverless.socket.host}", {self.profiles.driverless.socket.port}, "{self.profiles.driverless.tab_user}")
                            connection.connect();
                            """

            from selenium_injector.utils.utils import read
            utils_js = read("files/js/utils.js")
            self.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument",
                                 {"source": "(function(){%s})()" % (utils_js + self.profiles.driverless.connection_js + config)})

    def get_cookies(self, urls:typing.List[str] = None) -> typing.List[dict]:
        arg = {}
        if urls:
            arg["urls"] = urls
        return self.execute_cdp_cmd("Network.getAllCookies", arg)['cookies']

    def add_cookie(self, cookie_dict:dict) -> None:
        self.execute_cdp_cmd("Network.setCookie",cookie_dict)

    def delete_cookie(self, name:str, url:str=None, domain:str=None, path:str=None) -> None:
        arg = {"name": name}
        if url:
            arg["url"] = url
        if domain:
            arg["domain"] = domain
        if path:
            arg["path"] = path
        self.execute_cdp_cmd("Network.deleteCookies", arg)

    def delete_all_cookies(self) -> None:
        self.execute_cdp_cmd("Network.clearBrowserCookies", {})

    def quit(self) -> None:
        if "profiles" in self.__dir__():
            if "driverless" in self.profiles.__dir__():
                # noinspection PyUnresolvedReferences
                self.profiles.driverless.stop()
        super().quit()

class profiles:
    # noinspection PyShadowingNames
    def __init__(self, driver, profile, cdp_handler=None):

        from selenium_interceptor.interceptor import cdp_listener
        from selenium_profiles.scripts.driver_utils import requests, actions

        self._driver = driver
        self._profile = profile

        self._seleniumwire = None

        if cdp_handler:
            self.cdp_handler = cdp_handler
        elif "profiles" in driver.__dir__():
            self.cdp_handler = driver.profiles.cdp_handler
        else:
            from selenium_profiles.scripts.profiles import cdp_handler
            self.cdp_handler = cdp_handler(self._driver)

        self.cdp_listener = cdp_listener(driver=self._driver)
        self.actions = actions(self._driver)

        requests = requests(self._driver)
        self.fetch = requests.fetch

        if "proxy" in self._driver.__dir__():
            self._seleniumwire = True


    # noinspection PyShadowingNames
    def apply(self, profile: dict):
        """
        apply options after driver already started
        :param profile: selenium-profiles options
        """
        from selenium_profiles.utils.utils import valid_key
        valid_key(profile.keys(), ["cdp", "options"], "profile (selenium-profiles)")
        if "options" in profile.keys():
            warnings.warn('profile["options"] can\'t be applied when driver already started')
        if "cdp" in profile.keys():
            # noinspection PyUnresolvedReferences
            self.cdp_handler.apply(profile["cdp"])

    def get_profile(self):
        from selenium_profiles.utils.utils import read
        js = read('js/export_profile.js', sel_root=True)
        return self._driver.execute_async_script(js)

    @property
    def _driverless(self):
        if "profiles" in self._driver.__dir__():
            if "driverless" in self._driver.profiles.__dir__():
                return self._driver.profiles.driverless
    @property
    def _dynamic_proxies_supported(self):
        if self._driverless or self._seleniumwire:
            return True

    def set_proxy(self, options):
        if not self._dynamic_proxies_supported:
            raise ModuleNotFoundError("dynamic proxies only supported with seleniumwire or selenium-injector enabled")
        else:
            return NotImplementedError("setting proxies dynamically not implemented yet")

    @property
    def proxy(self):
        def make_proxy(proxy_dict:dict or None):
            if proxy_dict:
                defdict = defaultdict(lambda :"")
                defdict.update(proxy_dict)
                parsed = defdict["scheme"] + "://" + str(defdict["port"]) +":"+defdict["host"]
                return parsed

        if self._seleniumwire:
            proxies = defaultdict(lambda: None)
            proxies.update(self._driver.proxy)
            if proxies["no_proxy"]:
                # noinspection PyUnresolvedReferences
                proxies["bypass_list"] = proxies["no_proxy"].split(",")
            del proxies["no_proxy"]
            if not proxies["http"] or proxies["https"]:
                proxies["mode"] = "system"
            return  dict(proxies)

        elif self._driverless:
            proxy = self._driverless.proxy
            mode = proxy.mode
            if mode == "fixed_servers":
                rules = defaultdict(lambda :None)
                rules.update(proxy.rules)
                bypass_list = rules["bypassList"]
                if not bypass_list:
                    bypass_list = []
                if rules["singleProxy"]:
                    # noinspection PyTypeChecker
                    single = make_proxy(rules["singleProxy"])
                    return {"http": single, "https": single, "ftp":single,
                            "mode":mode, "bypass_list":bypass_list}
                else:
                    return {"http": make_proxy(rules["proxyForHttp"]), "https": make_proxy(rules["proxyForHttps"]), "ftp": make_proxy(rules["proxyForFtp"]),"fallback_proxy":make_proxy(rules["fallbackProxy"]),
                            "mode": mode, "bypass_list":bypass_list}
            else:
                return {"mode":mode}
        else:
            return




