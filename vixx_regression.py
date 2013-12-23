import csv
import datetime
import itertools
import utility
import math

class ResultSet(object):
	def __init__(self, results):
		self.results = sorted(results)

		assert len(set(x.expiration_date for x in results)) == len(results), "Results unique on expiration date"

	def __iter__(self):
		return iter(self.results)

class Result(object):
	def __init__(self, quote_date, expiration_date, return_):
		assert quote_date < expiration_date, "Quote date should occur strictly before expiration date"

		self.quote_date = quote_date
		self.expiration_date = expiration_date
		self.return_ = return_
	
	def __repr__(self):
		return str(self)

	def __str__(self):
		return "<Result with quote from {0}, expired at {1}, with return of {2}>".format(self.quote_date, self.expiration_date, self.return_)

	def __cmp__(self, other):
		return cmp(self.quote_date, other.quote_date)


def string_to_time(string):
		return datetime.datetime.strptime(string, "%Y-%m-%d")

def make_result(line):
	return Result(string_to_time(line[0]), string_to_time(line[1]), float(line[2]))

def load_returns():
	return_file = "iron_condor_results.csv"
	with open(return_file, "rb") as csv_file:
		return ResultSet([make_result(line) for line in csv.reader(csv_file)])

def load_vix():
	vix_file = "vix.csv"
	with open(vix_file, "rb") as csv_file:
		return VixSeries([make_vixday(line) for line in csv.reader(csv_file) if is_vixday(line)])

class VixDay(object):
	""" A yahoo downloaded historical price for a single day on the VIX """
	def __init__(self, date, open_, high, low, close, adj_close):

		assert high >= low, "High should be lower than close, high : " + str(high) + " and low : " + str(low)
		assert high >= close >= low, "Close should be between high and low"
		assert high >= open_ >= low, "Open should be between high and low"
		assert high >= adj_close >= low, "Adjusted Close should be between high and low"


		#this is for the vixx only
		assert adj_close == close, "Close should equal adjusted close"

		self.date = date
		self.open_ = open_
		self.high = high
		self.low = low
		self.close = close
		self.adj_close = adj_close

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "<VixDay object with date {0}, open {1}, high {2}, low {3}, close {4}, and adjusted close {5} >".format(self.date, self.open_, self.high, self.low, self.close, self.adj_close) 

	def __cmp__(self, other):
		return cmp(self.date, other.date)

class VixSeries(object):
	def __init__(self, vixdays):

		self.vixdays = sorted(vixdays)

		assert self.vixdays[-1] > self.vixdays[0], "Vixdays should be in order from earliest to latest"
		assert len(set([x.date for x in vixdays])) == len(vixdays), "Vixdays should be unique by date"

	def __getitem__(self, date):
		return next(vixday for vixday in self.vixdays if vixday.date == date)

	def nearest(self, date):
		return utility.find_nearest_of(date, self.vixdays, lambda x: x.date)

	#TODO: add and use nearest before to prevent using dates we really haven't 'seen' yet

def make_vixday(line):
	""" Constructs a VixDay object from a csv read line. """
	return VixDay(string_to_time(line[0]), 
		      float(line[1]), 
		      float(line[2]), 
		      float(line[3]),
		      float(line[4]),
		      float(line[6])) 

def is_vixday(line):
	""" Returns true if the line represents a vixday """
	return line[0] != "Date"

def growth(begin, end):
	return (end - begin) / begin

def make_regression_series():
	vix = load_vix()
	results = load_returns()

#r squared 10.378
#p value .0013, .012751

#.009, .109

	return [(r.return_, vix.nearest(r.quote_date - datetime.timedelta(1)).close,
		            growth(vix.nearest(r.quote_date - datetime.timedelta(26)).close, vix.nearest(r.quote_date - datetime.timedelta(1)).close)) for r in results]		
#			    vix[r.quote_date].close * (growth(vix.nearest(r.quote_date - datetime.timedelta(26)).close, vix[r.quote_date].close))) for r in results]


	#12-1 month was not statistically significant
	#36-12 month was not statistically significant
	#36-1 month was not statistically significant
	#lags of return 1-4 are not statistically significant

def one_day_bar(vix):
	return (vix.close - vix.low) / (vix.high - vix.low)

def bar_strength(vix, date, lags):
	vix_levels = [vix.nearest(date - datetime.timedelta(lag_)).close for lag_ in range(1, lags)]
	return (vix.nearest(date).close - min(vix_levels)) / (max(vix_levels) - min(vix_levels))

def make_x_y(series):
	unpacked = zip(*series)
	return (unpacked[0], zip(*unpacked[1:]))
