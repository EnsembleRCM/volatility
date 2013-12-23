#NEW FEATURES:
# - Cross validation of model data
# - Backtest the actual trading strategy over the last 5 years for expected returns
# - Assymetric condors
# - New regressors:
#   + implied volatility from historical options data
#   + calculated volatility from the SPY
#   + range for the SPY (non-parametric of above)
#   + potential returns (premium and risk is known at the time you get in the position)
#   + Non-parametric monte carlo with a SPY forecasting model for a black sholes like solution
#   + credit spread size (as a measure of the differential in contracts)
#   + bid-ask spread, open interest, volume
# - Models:
#   + Support Vector Regression of potential return
#   + Support vector machine of chance of loss, chance of gain
#   + Decision / Random forest of above
#   + Narrow spread size to be automatically more in the money
#   + Regress on *premium* rather than return. Then only sell condors who's premiums are higher than you predict *and* have high expected returns (and low expected failure)
#   + Use logit/probit for chance success/failure rather than linear probability
# - Forward looking:
#   + forecast the vix to better predict whether we should wait for tomorrow
# - Fix errors
#   + Nearest should return nearest *before*, otherwise we look into the future
#   + Get rid of date errors by detecting and removing weeklies when I can't regress on them

import sys
import csv
import datetime
import itertools
import utility
import math
import ols
import numpy
import urllib
import live_yahoo
import IronCondor
import operator
import urllib

class ResultSet(object):
	def __init__(self, results):
		self.results = sorted(results)

	def __iter__(self):
		return iter(self.results)

class Result(object):
	def __init__(self, days_out, body_spread, wingspan, quote_date, expiration_date, return_):
		assert quote_date < expiration_date, "Quote date should occur strictly before expiration date"

		self.days_out = days_out
		self.body_spread = body_spread
		self.wingspan = wingspan
		self.quote_date = quote_date
		self.expiration_date = expiration_date
		self.return_ = return_
	
	def __repr__(self):
		return str(self)

	def __str__(self):
		return "<Result with body_spread of {0} and wingspan of {1}>".format(self.body_spread, self.wingspan)

	def __cmp__(self, other):
		return cmp(self.quote_date, other.quote_date)


def string_to_time(string):
		return datetime.datetime.strptime(string, "%Y-%m-%d")

def make_result(line):
	return Result(int(line[0]), float(line[1]) * 100, int(line[2]), string_to_time(line[3]), string_to_time(line[4]), float(line[5]))

def make_fake_result(quote_date, expiration_date, body_spread, wingspan):
	return Result((expiration_date - quote_date).days, body_spread * 100, wingspan, quote_date, expiration_date, 0.0)

def is_return(line):
	return line[0] != "days_out"

def load_returns():
	return_file = "iron_condor_results_cumulative.csv"
	with open(return_file, "rb") as csv_file:
		return ResultSet([make_result(line) for line in csv.reader(csv_file) if is_return(line)])

def load_prices(ticker):
	today = datetime.date.today()
	url = "http://ichart.finance.yahoo.com/table.csv?s={0}&d={1}&e={2}&f={3}&g=d&a=0&b=29&c=1993&ignore=.csv".format(urllib.quote(ticker), today.month-1, today.day+1, today.year) 
	print url
	vix_url = urllib.urlopen(url)
#	vix_file = "vix.csv"
	#with open(vix_file, "rb") as csv_file:

	return VixSeries([make_vixday(line) for line in csv.reader(vix_url) if is_vixday(line)])

class VixDay(object):
	""" A yahoo downloaded historical price for a single day on the VIX """
	def __init__(self, date, open_, high, low, close, adj_close):

		assert high >= low, "High should be lower than close, high : " + str(high) + " and low : " + str(low)
		assert high >= close >= low, "Close should be between high and low"
		assert high >= open_ >= low, "Open should be between high and low"

		#TODO: renable for vix only day
		#assert high >= adj_close >= low, "Adjusted Close should be between high and low"


		#this is for the vixx only
		#assert adj_close == close, "Close should equal adjusted close"

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
		self._cache = {}

		assert self.vixdays[-1] > self.vixdays[0], "Vixdays should be in order from earliest to latest"
		assert len(set([x.date for x in vixdays])) == len(vixdays), "Vixdays should be unique by date"

	def __getitem__(self, date):
		return next(vixday for vixday in self.vixdays if vixday.date == date)

	def nearest(self, date):
		if date not in self._cache:
			self._cache[date] = utility.find_nearest_of(date, self.vixdays, lambda x: x.date)
		return self._cache[date]

	#	return utility.find_nearest_of(date, self.vixdays, lambda x: x.date)

	#TODO: add and use nearest before to prevent using dates we really haven't 'seen' yet

class Lag(object):
	def __init__(self, series, lag):
		self._series = series
		self._lag = lag

	def nearest(self, date):
		return self._series.nearest(date - datetime.timedelta(self._lag))
	
class Growth_(object):
	def __init__(self, early_series, later_series):
		self._early_series = early_series
		self._later_series = later_series

	def nearest(self, date):
		return growth(self._early_series.nearest(date), self._later_series.nearest(date))

class Take(object):
	def __init__(self, series, key):
		self._series = series
		self._key = key

	def nearest(self, date):
		return self._key(self._series.nearest(date))


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

def print_date_grab_return_(r):
#	print r.quote_date
	return r.return_

def is_earnings_season(date_):
	return date_.month in [1, 4, 7, 10]

def is_quarter(quarter, date_):

	end = quarter * 3 #end month of the quarter is 3 times the quarter
	begin = end - 2 #begin month of the quarter is two months before that

	return date_.month in range(begin, end + 1) #range is exclusive of the end
	
#	quarters = {1: [1,2,3], 2: [4,5,6], 3: [7,8,9], 4: [10,11,12]}
#	return date_.month in quarters[quarter]

	#q1 is jan, feb, march
	#q2 is april, may, june
	#q3 is july, august, sept
	#q4 is october, nov, dec

class TransformedSeries(object):
	def __init__(self, vix):
		self._vix = vix

	def generate_transformed_point(self, r):
		vix_close = Take(self._vix, lambda x: x.close)
		days_out = lambda d1, d2: (d1 - d2).days
		prev_period_vix_growth = lambda r: Growth_(Lag(vix_close, days_out(r.expiration_date, r.quote_date)), Lag(vix_close,1)).nearest(r.quote_date)

		return [#math.log(max(r.return_, .00000000000000000001)), 
			#r.return_,
			#r.return_ > 1.0,
			#r.return_ < 0.01,
			r.days_out, #days out from the trade
			r.days_out * Lag(vix_close,1).nearest(r.quote_date),
			r.days_out * Lag(vix_close,1).nearest(r.quote_date)**2,
			r.days_out * prev_period_vix_growth(r),
			r.days_out ** 2,
			r.wingspan,
		        r.wingspan ** 2,
			#r.wingspan * Lag(vix_close,1).nearest(r.quote_date), #doesn't work in linear prob
			#r.wingspan * Lag(vix_close,1).nearest(r.quote_date) ** 2, #Not meaningful, l
			#r.wingspan * prev_period_vix_growth(r), #Not statisticially significant
			r.body_spread,
			r.body_spread ** 2,
			r.body_spread * Lag(vix_close, 1).nearest(r.quote_date),
			#r.body_spread * Lag(vix_close, 1).nearest(r.quote_date) ** 2, #Not statisticially significant
			#r.body_spread * prev_period_vix_growth(r), #doesn't work in linear prob
			#r.wingspan * r.body_spread, #not useful in linear prob model
			r.days_out * r.body_spread,
			r.wingspan * r.days_out,
			#(r.days_out ** 2) * r.body_spread, #doesn't work in the log model
			#kinks in these variables? ^^^
			Lag(vix_close, 1).nearest(r.quote_date), 
			Lag(vix_close, 1).nearest(r.quote_date) ** 2,
			#prev_period_vix_growth(r), #doesn't work in log model
			#prev_period_vix_growth(r) ** 2, #above doesn't work in linear prob model with this
			Growth_(Lag(vix_close, 365), Lag(vix_close,30)).nearest(r.quote_date),
			Growth_(Lag(vix_close, 1080), Lag(vix_close,365)).nearest(r.quote_date),
			is_earnings_season(r.quote_date),
			#is_quarter(1, r.quote_date),
			#is_quarter(2, r.quote_date), #quarter 4 doesn't work in linear prob model with this
			#is_quarter(3, r.quote_date),
			#is_quarter(4, r.quote_date), #quarter 4 doesn't work in the log model at all.
			#r.quote_date.month == 1, #MONTHS LEFT OUT IN FAVOR OF QUARTER AND EARNINGS MONTH MODEL
			#r.quote_date.month == 2, 
			#r.quote_date.month == 3, 
			#r.quote_date.month == 4, 
			#r.quote_date.month == 5, 
			#r.quote_date.month == 6, 
			#r.quote_date.month == 7, 
			#r.quote_date.month == 8, 
			#r.quote_date.month == 9, 
			#r.quote_date.month == 10, 
			#r.quote_date.month == 11, 
			r.quote_date.month == 12, #December left in because it was relatively large
			r.expiration_date.year - 2008, # for r in results] #CONTROL
			]

def make_regression_series(y_gen, x_gen, results):
	

	return [[y_gen(r)] + x_gen.generate_transformed_point(r) for r in results]
		 #r.days_out ** 2, #taylor 2 expansion of days out
		 #(r.days_out ** 2) * (Lag(vix_close,1).nearest(r.quote_date)),
		 #r.days_out * prev_period_vix_growth(r), #interaction between days_out and vix growth
		 #r.body_spread, #target % of the body spread around the underlying this guy back in
		 #r.body_spread ** 2, #taylor 2 expansion of days out
		 #r.body_spread * Lag(vix_close,1).nearest(r.quote_date), #interaction between body spread and vix
		 #r.body_spread * prev_period_vix_growth(r), #interaction between body_spread and vix growth
		 #r.wingspan, #point spread between the calls or puts of the wings
		 #r.wingspan ** 2, 
		 #r.wingspan * r.days_out,
	         #Growth_(Lag(vix_close, 30), Lag(vix_close,1)).nearest(r.quote_date),
		 #Lag(vix_close, 1).nearest(r.quote_date) ** 2, #taylor 2 expansion of Vix

	#initial model
	#12-1 month was not statistically significant
	#36-12 month was not statistically significant
	#36-1 month was not statistically significant
	#lags of return 1-4 are not statistically significant
	#no month was statistically significant, although april was close

def fit(model, row, vix):
	#print row
	#print model.b
	transform = TransformedSeries(vix)
	#print transform.generate_transformed_point(row)
	return numpy.dot(model.b, [1,] + transform.generate_transformed_point(row))

def deciles(m, results, inputs):

	print "Generating fit results"
	fitset = sorted([(fit(m, r, inputs),r.return_) for r in results], key=lambda x: x[0])

	decile_size = len(fitset) / 10

	print "Generating deciles"
#	decile_averages = [(fitset[d*decile_size][0], fitset[(d+1)*decile_size][0],numpy.mean([f[1] for f in fitset[d*decile_size:(d+1)*decile_size]])) for d in range(10)]
	decile_proportions = [(fitset[d*decile_size][0], fitset[(d+1)*decile_size][0], float(len([f[1] for f in fitset[d*decile_size:(d+1)*decile_size] if f[1] > 0.0])) / len(fitset[d*decile_size:(d+1)*decile_size])) for d in range(10)]

	#lifts = [(d2[2] - d1[2]) / d1[2] for d1,d2 in zip(decile_averages[:-1],decile_averages[1:])] 
	lifts = [(d2[2] - d1[2]) / max(d1[2], 0.0001) for d1,d2 in zip(decile_proportions[:-1],decile_proportions[1:])] 


	return fitset, decile_proportions, lifts

def chance_of_failure(r):
	return r.return_ < 0.001

def build_model(y_gen, x_gen, results):

	series = make_regression_series(y_gen, x_gen, results)
	y,x = make_x_y(series)

	m = ols.ols(y,x,"returns", ["Days out", "Days out * VIX", "Days out * Vix^2", "Days out * Prev Period", "Days out^2",
		                    "Wingspan", "Wingspan^2",
				    "Body Spread", "Body Spread^2", "Body Spread * Lag",
				    "Days out * Body Spread", "Wingspan * Days Out", 
				    "VIX", "VIX^2", "VIX 12-1 Month Growth", "VIX 36-12 month growth",
				    "Is Earnings?", "Is December?", "Expiration Year (CONTROL)"])
	m.summary()
	return m

def chance_of_failure_model(vix, results):
	x_gen = TransformedSeries(vix)
	y_gen = chance_of_failure

	return build_model(y_gen, x_gen, results)

def linear_return(vix, results):
	x_gen = TransformedSeries(vix)
	y_gen = lambda r: r.return_

	return build_model(y_gen, x_gen, results)

def log_return(vix, results):
	x_gen = TransformedSeries(vix)
	y_gen = lambda r: math.log(max(r.return_,0.000000001))

	return build_model(y_gen, x_gen, results)

def linear_prob_positive_return(vix, results):
	x_gen = TransformedSeries(vix)
	y_gen = lambda r: r.return_ > 1.0

	return build_model(y_gen, x_gen, results)

def performance(results, go_no_go):

	print "running performance metrics"
	vix = load_prices("^VIX")

	on_go_trades = [r.return_ for r in results if go_no_go(r)] 
	on_no_go_trades = [r.return_ for r in results if not go_no_go(r)]

#	return [numpy.mean(on_go_trades), 
#	        numpy.mean(on_no_go_trades), 
#		len(on_go_trades), 
#		len(on_no_go_trades), 
#		len(results.results), 
#		float(len(on_go_trades)) / len(results.results),
#		(numpy.mean(on_go_trades) - numpy.mean(on_no_go_trades)) / numpy.mean(on_no_go_trades),
#		numpy.std(on_go_trades)]
	return {"Trade Rate":float(len(on_go_trades)) / len(results.results),
		"Expected Return":numpy.mean(on_go_trades),
		"Expected Volatility":numpy.std(on_go_trades),
		"Information Ratio":numpy.mean(on_go_trades) / numpy.mean(on_no_go_trades),
		"Sharp Ratio":numpy.mean(on_go_trades)/numpy.std(on_go_trades),
		"Failure Rate":float(len([r for r in on_go_trades if r < 0.00001])) / len(on_go_trades)}


#def go_no_go(

def performance_metrics():
	vix = load_prices("^VIX")
	results = load_returns()

	m1 = chance_of_failure_model(vix, results)
	m2 = linear_return(vix, results)
	#m3 = log_return(vix, results)
	m4 = linear_prob_positive_return(vix, results)

	#return performance(results, lambda r: fit(m1, r, vix) < .1188)
#	return performance(results, lambda r: fit(m2, r, vix) > 1.002)
	#return performance(results, lambda r: fit(m2, r, vix) > 1.002 and fit(m1, r, vix) < .1188)
	#return performance(results, lambda r: fit(m3, r, vix) > -7.62)
	#return performance(results, lambda r: fit(m4, r, vix) > .68)
	#return performance(results, lambda r: fit(m2, r, vix) > 1.002 and fit(m4, r, vix) > .68)
	#return performance(results, lambda r: fit(m1, r, vix) < .1188 and fit(m3, r, vix) > -7.62)
	#return performance(results, lambda r: fit(m1, r, vix) < .1188 and fit(m2, r, vix) > 1.002 and fit(m3, r, vix) > -7.62 and fit(m4, r, vix) > .68)
	return performance(results, lambda r: fit(m1, r, vix) < .1188 and fit(m2, r, vix) > 1.002 and fit(m4, r, vix) > .68)
#	return deciles(m, results, vix)


class SpreadGen(object):
	def __init__(self):
		self.vix = load_prices("^VIX")
		self.spy = load_prices("SPY")
		self.returns = load_returns()

		self.failure_model = chance_of_failure_model(self.vix, self.returns)
		self.linear_return = linear_return(self.vix, self.returns)

		todays_vix = live_yahoo.get_symbol_price("VIX")
		#shove this in there to get up to the minute (er, 20 minutes) readings
		#NOTE: this isn't completely statistically valid
		self.vix.vixdays[-1].close = todays_vix

	def suggest_spread(self, quote_date, expiration_date):
		body_spread_range = numpy.arange(.005, .055, .005)
		wingspan_range = numpy.arange(1,6,1)

		

		return [(fit(self.linear_return, make_fake_result(quote_date, expiration_date, r[0], r[1]), self.vix), make_fake_result(quote_date, expiration_date, r[0], r[1])) for r in itertools.product(body_spread_range, wingspan_range) if fit(self.failure_model, make_fake_result(quote_date, expiration_date, r[0], r[1]), self.vix) < .1188 and fit(self.linear_return, make_fake_result(quote_date, expiration_date, r[0], r[1]), self.vix) > 1.002]
	
	def print_spread(self, spread, top=3):

		if len(spread) == 0:
			print "No valid trades for quote date"
			return

		print "Average Return is " + str(numpy.mean([x[0] for x in spread]))
		results = sorted(spread, key=lambda x:x[0], reverse=True)
		todays_spy = live_yahoo.get_symbol_price("SPY")

		for r in results[:top]:
			sp = spread_percent = r[1].body_spread / 100.0
			print "Expiration date", r[1].expiration_date
			print "Body spread " + str(r[1].body_spread)
			print "Wingspan " + str(r[1].wingspan)
			print "Sell call spread at {0}\n with spread at {1},\n sell put spread at {2}\n with spread at {3},\n expected return {4}".format(round(todays_spy * (1.0 + sp)),
				 													  round((todays_spy * (1.0 + sp)) + r[1].wingspan),
																	  round(todays_spy * (1.0 - sp)),
																	  round((todays_spy * (1.0 - sp)) - r[1].wingspan),
																	  r[0])

def spread_for_today(spread_gen, expiration_date, quote_date, spy_value):
	#return spread_gen.suggest_spread(datetime.datetime.today(), expiration_date)
	return filter_liquidity(spread_gen.suggest_spread(datetime.datetime.today(), expiration_date), quote_date, spy_value)

def filter_liquidity(spread, quote_date, spy_value):
	current_options = live_yahoo.main()


	print "filtering options based on what prices are available"
	print "number of spreads found that pass model", len(spread)
	try:
		maturity = next(opt for opt in current_options if opt.expiration_date() == spread[0][1].expiration_date)
	except:
		print "cannot find optiosn for {0} among list of {1}".format(spread[0][1].expiration_date, str([x.expiration_date() for x in current_options]))
		return []


	print maturity
	results = []
	for s in spread:
		try:
			print s[1].body_spread, s[1].wingspan
			ic = IronCondor.make_short_iron_condor(maturity, spy_value, float(s[1].body_spread) / 100.0, s[1].wingspan)
		except Exception as e:
			print e
			print type(e)
			print "Unable to make short iron condor with {0} body spread and {1} wingspan at maturity {2} and value {3}".format(s[1].body_spread, s[1].wingspan, maturity.expiration_date(), spy_value)
			continue
		print "model expects {0} but option worth {1}".format(s[0], 1.0 + ic.max_return())
		if 1.0 + ic.max_return() > s[0]:
			results.append(s)


	print "number of spreads found that pass premium requirement", len(results)

	return results





def spread_for_tomorrow(spread_gen, expiration_date, quote_date, spy_value):
	#return spread_gen.suggest_spread(datetime.datetime.today()+datetime.timedelta(1), expiration_date)
	return filter_liquidity(spread_gen.suggest_spread(datetime.datetime.today()+datetime.timedelta(1), expiration_date), quote_date, spy_value)

def gen_spreads2(expiries=None):

	gen = SpreadGen()
#	expiration_date = datetime.datetime(2013,10,11)

	spy = live_yahoo.get_symbol_price("SPY")
	available_dates = [x.expiration_date() for x in live_yahoo.main()]
	available_spreads = reduce(operator.add, [spread_for_today(gen, expiry, datetime.datetime.today(), spy) for expiry in available_dates])
	gen.print_spread(available_spreads)

#	if not expiries:
#		for arg in sys.argv[1:]:
#			format_ = "%m/%d/%Y"
#			expiration_date = datetime.datetime.strptime(arg, format_)
#			print "For expiration date " + arg
#			gen.print_spread(spread_for_today(gen, expiration_date, datetime.datetime.today(), spy))
#			print "\n and for the next day\n "
#			gen.print_spread(spread_for_tomorrow(gen, expiration_date, datetime.datetime.today(), spy))
#			print "\n"
#	else:
#		for arg in expiries:
#			format_ = "%m/%d/%Y"
#			expiration_date = arg
#			print "For expiration date " + str(arg)
#			gen.print_spread(spread_for_today(gen, expiration_date, datetime.datetime.today(), spy))
#			print "\n and for the next day\n "
#			gen.print_spread(spread_for_tomorrow(gen, expiration_date, datetime.datetime.today(), spy))
#			print "\n"

def gen_spread():

	print "Loading data"
	vix = load_prices("^VIX")
	spy = load_prices("SPY")
	results = load_returns()

	

	print "Training models"
	m1 = chance_of_failure_model(vix, results)
	m2 = linear_return(vix, results)


	quote_date = datetime.datetime.today()
#	expiration_date = datetime.datetime(2013,9,21)
	expiration_date = datetime.datetime(2013,10,11)

	body_spread_range = numpy.arange(.005, .055, .005)
	wingspan_range = numpy.arange(1,6,1)

	print "Searching for spreads with quote date " + str(quote_date)
	results = []
	for bodyspread,wingspan in itertools.product(body_spread_range, wingspan_range):
		r = make_fake_result(quote_date, expiration_date, bodyspread, wingspan)
		if fit(m1,r,vix) < .1188:
			f = fit(m2,r,vix)
			if f > 1.002:
				results.append((fit(m2, r, vix), r))

	results = sorted(results, key=lambda x:x[1].body_spread,reverse=True)

	print "Average Return for today is " + str(numpy.mean([x[0] for x in results]))
	quote_date = datetime.datetime.today() + datetime.timedelta(1)
	expiration_date = datetime.datetime(2013,10,11)

	print "Searching for spreads with quote date " + str(quote_date)
	
	results1 = []
	for bodyspread,wingspan in itertools.product(body_spread_range, wingspan_range):
		r = make_fake_result(quote_date, expiration_date, bodyspread, wingspan)
		if fit(m1,r,vix) < .1188:
			f = fit(m2,r,vix)
			if f > 1.002:
				results1.append((fit(m2, r, vix), r))

	
	print "Average Return for tommorrow is " + str(numpy.mean([x[0] for x in results1]))

	results = sorted(results, key=lambda x:x[1].body_spread)
	todays_spy = spy.nearest(quote_date).close

	for r in results[:5]:
		sp = spread_percent = r[1].body_spread / 100.0
		print "Body spread " + str(r[1].body_spread)
		print "Wingspan " + str(r[1].wingspan)
		print "Sell call spread at {0}\n with spread at {1},\n sell put spread at {2}\n with spread at {3},\n expected return {4}".format(round(todays_spy * (1.0 + sp)),
				 													  round((todays_spy * (1.0 + sp)) + r[1].wingspan),
																	  round(todays_spy * (1.0 - sp)),
																	  round((todays_spy * (1.0 - sp)) - r[1].wingspan),
																	  r[0])
	
	return results


def main():
	return gen_spreads2()



def one_day_bar(vix):
	return (vix.close - vix.low) / (vix.high - vix.low)

def bar_strength(vix, date, lags):
	vix_levels = [vix.nearest(date - datetime.timedelta(lag_)).close for lag_ in range(1, lags)]
	return (vix.nearest(date).close - min(vix_levels)) / (max(vix_levels) - min(vix_levels))

def make_x_y(series):
	unpacked = zip(*series)
	return (numpy.array(unpacked[0]), numpy.array(zip(*unpacked[1:])))

if __name__ == "__main__":
	main()
