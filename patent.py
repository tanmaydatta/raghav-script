import os
import sys
from processors.site_gb import SiteGBProcessor # http://www.ipo.gov.uk
from processors.site_fi import SiteFIProcessor # http://patent.prh.fi
from processors.site_wo import SiteWOProcessor
from processors.site_ep import SiteEPProcessor
from processors.site_us import SiteUSProcessor
from processors.site_usfee import SiteUSFEEProcessor

from processors import CapchaRequiredException
from saver import Saver
from utils import proxy_list
from utils.proxy_list import NoMoreProxiesException
from utils import csv_list
from selenium import webdriver

driver = webdriver.PhantomJS()

captcha_login = "webbug08"
captcha_pwd = "password123"


try:
    REQUESTS_PER_MINUTE = 0 # if proxy in use, then for a proxy
    MAX_PROXY_USAGE_NUMBER = 15 # how many times use the same proxy in a row
    USE_PROXY = False
    DO_DOWNLOAD = False
    BASE_DIR = os.path.dirname(os.path.realpath(__file__))
    READYNUMS_FILENAME = os.path.join(BASE_DIR, "ready_nums.csv")
    FAILEDNUMS_FILENAME = os.path.join(BASE_DIR, "failed_nums.csv")
    PROXIES_FILENAME = os.path.join(BASE_DIR, "proxy_list.txt")
    INPUT_FILENAME = os.path.join(BASE_DIR, "Input.csv")
    
    
    
    _arg_to_var = {
            "-i": "INPUT_FILENAME",
            "-mpu": ("MAX_PROXY_USAGE_NUMBER", int),
            "-rpm": ("REQUESTS_PER_MINUTE", float),
            "-d": ("DO_DOWNLOAD", bool),
            "-p": ("USE_PROXY", bool),
        }
    
    _file_path_args = ["-i"]
    
    if len(sys.argv) >= 2 and sys.argv[1] in ("-help", "-h"):
        print("""
    Arguments:
        -i - input file;
            (default: %s)
        -p - use proxy: 0-False 1-True.
            (default: %s)
        -mpu - maximum usage of same proxy in row(if less then 2 proxies, ignored);
            (default: %d)
        -rpm - requests per minute(if proxy in use, then for a proxy);
            (0 - no limit, default: %0.2f)
        -d - file download: 0-False 1-True.
            (default: %s)
    
    
    No spaces allowed near equal sign, example:
    
        python3 patent.py -i="input file.csv" -d=0 -rpm=2.5 -mpu=10
        """ % (INPUT_FILENAME, MAX_PROXY_USAGE_NUMBER, REQUESTS_PER_MINUTE,
                1 if DO_DOWNLOAD else 0, 1 if USE_PROXY else 0))
        sys.exit(0)
    
    
    for arg in sys.argv[1:]:
        found = False
        for av in _arg_to_var:
            if not arg.startswith(av):
                continue
            
            try:
                key, val = arg.split('=', 1)
            except ValueError:
                print("Wrong argument: %s" % arg)
                sys.exit(2)
                
            found = True
            
            if key in _file_path_args:
                globals()[_arg_to_var[av]] = os.path.join(BASE_DIR, val)
            else:
                globals()[_arg_to_var[av][0]] = _arg_to_var[av][1](val)
    
                
        if not found:
            print("Cannot parse argument: %s" % arg)
            sys.exit(2)
    
    print("""
    Runnung with arguments:
        Input file: %s
        Use proxy: %s
        Requests per minute: %0.2f (if proxy in use, then for a proxy)
        Max. proxy usage: %d (if less then 2 proxies in use, ignored)
        Download files: %s
    """ % (INPUT_FILENAME,  USE_PROXY, REQUESTS_PER_MINUTE,
                                        MAX_PROXY_USAGE_NUMBER, DO_DOWNLOAD))
    
    
    if USE_PROXY:
        proxy_list.load_from_file(PROXIES_FILENAME)
    
    saver = Saver(autoflush=False)
    
    
    # mapping sites to their respective classes
    site_mapping = [
            #((types,), processing function)
            [("GBA", "GBP"),
                SiteGBProcessor(saver, REQUESTS_PER_MINUTE, MAX_PROXY_USAGE_NUMBER, 
                    do_download=DO_DOWNLOAD)],
            [("FIA", "FIP"),
                SiteFIProcessor(saver, REQUESTS_PER_MINUTE, MAX_PROXY_USAGE_NUMBER,
                    do_download=DO_DOWNLOAD, proxy_list=[])],
            [("WO"),
                SiteWOProcessor(saver, REQUESTS_PER_MINUTE, MAX_PROXY_USAGE_NUMBER,
                    do_download=DO_DOWNLOAD)],
            [("EPA"),
                SiteEPProcessor(saver, driver,
                    REQUESTS_PER_MINUTE, MAX_PROXY_USAGE_NUMBER,
                    do_download=DO_DOWNLOAD, proxy_list=[])],
            [("USA", "USPUB", "USPAT"),
                SiteUSProcessor(saver,
                    captcha_login=captcha_login, captcha_pwd=captcha_pwd,
                    do_download=DO_DOWNLOAD)],
            [("USFEE",),
                SiteUSFEEProcessor(saver,
                    REQUESTS_PER_MINUTE, MAX_PROXY_USAGE_NUMBER, 
                    do_download=DO_DOWNLOAD)],
        ]
    
    
    # reading input csv
    csv_data = csv_list.csv2list(INPUT_FILENAME)
    
    # getting nums
    CSV_HEADERS = ("Input/App. Num.", "Type", "Alias", "Patent Num.")
    csv_readynums = csv_list.csv2list_or_empty(READYNUMS_FILENAME,
            skip_first_line=True)
    #csv_readynums = [] ######
    csv_failednums = csv_list.csv2list_or_empty(FAILEDNUMS_FILENAME,
            skip_first_line=True)


    # processing input rows
    for row, row_no in zip(csv_data[1:], range(1, len(csv_data))):
        print("")
        
        if csv_list.get_tuple_row_index_of(row[:4], csv_readynums,
                force_length=True) != -1:
            
            if row[:4]:
                print("Number %s already processed." % str(row[:4]))
                
            continue
        
        
        # which package should process it?
        proc = None
        for sm in site_mapping:
            if row[1].strip().upper() in sm[0]:
                proc = sm[1]
                break
        
        if proc is None:
            print("%s #%d: %s" % ( "No processor found for row".upper(),
                                    row_no, str(row[:4])))
            print("")
            continue
    
        print("%s #%d: %s"  % ("Processing csv row".upper(), row_no,
                                                                str(row[:4])))
        
        try:
            if len(row) <= 3:
                proc.process_number(
                    row[0].strip(), row[1].strip().upper(), row[2].strip())
            else:
                proc.process_number(
                    row[0].strip(), row[1].strip().upper(), row[2].strip(),
                    row[3].strip())
        except CapchaRequiredException as e:
            print("")
            print("PROGRAM FAIL: %s" % str(e))
            #sys.exit(1)
            continue
        except NoMoreProxiesException as e:
            print("")
            print("No proxies exception: %s" % str(e))
            #sys.exit(1)
            continue
        except Exception as e:
            '''
            if not "No search result" in str(e):
                raise
            '''
            #raise
            print("FAILD TO PROCESS NUMBER: %s." % str((row[:4])))
            
            print("REASON: %s." % str(e))
            print("")
            
            save_row = row[:4]
            if len(save_row) < 4:
                save_row.append([])
                
            save_row.append(str(e))
            csv_failednums.append(save_row)
            csv_list.append_row_to_csv_file(FAILEDNUMS_FILENAME, save_row,
                CSV_HEADERS)
            print("")
            saver.cancel_changes()
            continue
        
    
        saver.flush()
        
        row_index = csv_list.get_tuple_row_index_of(row[:4], csv_failednums,
                                                            force_length=True)
        save_failed = (row_index != -1)
        
        while row_index != -1:
            del csv_failednums[row_index]
            
            row_index = csv_list.get_tuple_row_index_of(row[:4], csv_failednums,
                                                            force_length=True)
        
        
        if save_failed:
            csv_list.list2csv(FAILEDNUMS_FILENAME, csv_failednums, CSV_HEADERS)
            print("Successfully processed previously failed number: %s." %
                                                                str(row[:4]))
            
        csv_readynums.append(row)
        csv_list.append_row_to_csv_file(READYNUMS_FILENAME, row, CSV_HEADERS)
        #break
        print("")
        
finally:
    try:
        driver.close()
        
        for proc in site_mapping:
            try:
                proc[1].close()
            except:
                pass
            
    except:
        pass


print("") # empty line for better output
print("DONE.")








