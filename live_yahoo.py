from mechanize import Browser
from bs4 import BeautifulSoup
import datetime
import locale
import Options
import utility
import operator

class dumbOptionDay(object):
	def __init__(self, strike, name, last, change, bid, ask, volume, open_interest):
		self.strike = strike
		self.name = name
		self.last = last
		self.change = change
		self.bid = bid
		self.ask = ask
		self.volume = volume
		self.open_interest = open_interest

	def date(self):
		pass

	def is_call(self):
		#TODO: verify that the name has c or p, invariant
		return self.name.find("C") != -1

	def is_put(self):
		return not self.is_call()

#examples:
#SPY131019C00130000 -> vanilla, 10,19,2013, call, strike 130
#SPY7131019C00161000
#SPYJ131011C00166000

def is_call(option_name):
	return 'C' in option_name

def is_jumbo(option_name):
	""" Returns whether this option represents a jumbo option """
	return 'J' in option_name

def is_micro(option_name):
	""" Returns whether this option represents a micro option """
	return '7' == option_name[3]

def is_vanilla(option_name):
	""" Returns whether this option represents a normal option, not a jumbo or micro """
	return not is_micro(option_name) and not is_jumbo(option_name)

def get_expiration(option_name):
	""" Returns the expiration date for this option """
	start = 3 if is_vanilla(option_name) else 4
	length_of_date = 6
	date_str = option_name[start:start+length_of_date]
	return datetime.datetime.strptime(date_str, "%y%m%d")


def make_options_day(strike, name, last, change, bid, ask, volume, open_interest, quote_date, underlying_price):
	return Options.Day(name, underlying_price, Options.Call if is_call(name) else Options.Put, get_expiration(name), quote_date, strike, bid, ask, "*", volume, open_interest)

def is_optionday(row, quote_date, spy):
	try:
		r = as_optionday(row, quote_date, spy)
	except Exception as e:
		print e
		return False
	return True

def as_optionday(row, quote_date, underlying_price):
	text = [x.text for x in row]
	if len(text) != 8:
		raise Exception()

	return make_options_day(to_maybe_float(text[0]), str(text[1]), to_maybe_float(text[2]), to_maybe_float(text[3]), to_maybe_float(text[4]), to_maybe_float(text[5]), to_int(text[6]), to_int(text[7]), quote_date, underlying_price)

def to_int(i):
	return int(i.replace(",",""))
#	TODO:figure out locale's
#	return locale.atoi(i)

def to_maybe_float(f):
	if f == "N/A":
		return None
	return float(f)

def get_symbol_price(symbol):
	mech = Browser()
	url = "http://finance.yahoo.com/q?s={0}".format(symbol)

	page = mech.open(url)
	html = page.read()
	soup = BeautifulSoup(html)
	return float(soup.findAll("span",{"class":"time_rtq_ticker"})[0].text)

def main():
	today = datetime.datetime.today()
	dates = [today, datetime.datetime(today.year, today.month+1, today.day), datetime.datetime(today.year, today.month+2, today.day)]
	return reduce(operator.add, [grab_options_prices(date_) for date_ in dates])

def grab_options_prices(date_=datetime.datetime(2013,10,1)):
	mech = Browser()


	url = "http://finance.yahoo.com/q/op?s=SPY&m={0}-{1}".format(date_.year, date_.month)
	page = mech.open(url)

	html = page.read()
	soup = BeautifulSoup(html)

	tables = soup.findAll("table")
	#tables[4] ?
	#tables[8] ?
	#tables[9] ?
	#tables[12] ?
	#tables[13] ?
	#goes up to 17

	day = datetime.datetime.today()
	rows = [as_optionday(r, day, 0.0) for r in tables[4].findAll('tr') if is_optionday(r, day, 0.0)]
	rows = [r for r in rows if is_vanilla(r.option_name)]
	maturities = utility.sorted_groupby([r for r in rows], Options.Day.expiration_date)

	return [Options.make_quote(m[1]) for m in maturities]
