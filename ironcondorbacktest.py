import csv, pickle, functools, itertools, datetime, gc
from charts import *
from analysis import *
from utility import *
import os.path
import os
import operator
import random
import numpy.testing
import itertools
from Options import *
from IronCondor import *

def make_options_day(symbol, last_symbol_price, exchange, option_name, options_extension, options_type, expiration_date, quote_date, strike, last, bid, ask, volume, open_interest, implied_volatility, delta, gamma, theta, vega, alias):
	return OptionsDay(option_name
			 ,float(last_symbol_price)
		         ,Call if options_type == "call" else Put
		         ,to_date(expiration_date)
		         ,to_date(quote_date)
		         ,float(strike)
		         ,float(bid)
		         ,float(ask)
			 ,exchange
			 ,volume
			 ,open_interest)



def load_file(filename):
	with open(filename) as csvfile:
		csv_rdr = csv.reader(csvfile)
		next(csv_rdr)
#		return [make_options_day(option_name, last_symbol_price, options_type, expiration_date, quote_date, strike, bid, ask) for symbol, last_symbol_price, exchange, option_name, options_extension, options_type, expiration_date, quote_date, strike, last, bid, ask, volume, open_interest, implied_volatility, delta, gamma, theta, vega, alias in csv_rdr]
		return [make_options_day(*file_line) for file_line in csv_rdr]

def load_options(test):
	""" Returns a list of date option tuples, where the date is the expiration date and the options are options with that expiration date, sorted by quote_date """

	if(test):
		csv_files = ["SPY_2008.csv"]
	else:
		csv_files = ["SPY_2008.csv","SPY_2009.csv","SPY_2010.csv", "SPY_2011.csv", "SPY_2012.csv", "SPY_2013.csv"]
	csv_files = ("Batch_RF3RSL\\" + filename for filename in csv_files) 
	options = [option for csv_file in csv_files for option in load_file(csv_file)]

	return make_chain_from_options(options)

def sorted_groupby(list_, key_):
	return [(supirior, list(inferior)) for supirior, inferior in itertools.groupby(sorted(list_, key=key_), key=key_)]

def make_chain_from_options(options):
	""" Builds a chain data structure from a list of completely unsorted option days """

	options = sorted(options, key=OptionsDay.expiration_date)
	return Chain([make_maturity_from_options(expiration_date, options_) for expiration_date, options_ in sorted_groupby(options, OptionsDay.expiration_date)])
	
#	return Chain([Maturity(k, sorted(list(g), key=OptionsDay.quote_date)) for (k,g) in itertools.groupby(options, key=OptionsDay.expiration_date)])

def find_duplicates(list_, key=lambda x: x):
	""" Returns a list of objects that are duplicates in list_ """
	seen = set()
	seen_add = seen.add #optimization for function lookup
	# adds all elements it doesn't know yet to seen and all other to seen_twice
	seen_twice = set(x for x in list_ if key(x) in seen or seen_add(key(x)) )
	# turn the set into a list (as requested)
	return list( seen_twice )

def make_quote_from_options(quote_date, options):
	assert all(opt.quote_date() == options[0].quote_date() for opt in options)
	assert all(opt.expiration_date() == options[0].expiration_date() for opt in options)

	#we want to eliminate duplicate strike prices and take * 
#	duplicates = sorted(find_duplicates(options, key=OptionsDay.strike), key=OptionsDay.strike)

#	for d in duplicates:
#		print d.option_name, d.exchange, d.quote_date(), d.expiration_date(), d.strike()


	return make_quote(options)


def quote_for_date(options, target_date):
	""" For a list of options, returns the Quote object that matches the target_date """
	return make_quote([x for x in options if x.quote_date() == target_date])

def days_between(quote1, quote2):
	return abs((quote1.quote_date() - quote2.quote_date()).days)


def flatten(list_):
	""" Flattens a list by one layer """
	return reduce(list.__add__, list_)

class Maturity(object):
	""" A collection of options with the same expiration date. """
	def __init__(self, expiration_date, options):
		assert(all([option.expiration_date() == expiration_date for option in options]))
		#TODO: all options shoudl also have unique quote dates
		#TODO: last quote should
		#TODO: assert sorted
		assert not any([option.quote_date() > expiration_date for option in options])

		self._quotes = options
		self._expiration_date = expiration_date

	def with_quotes_after(self, date_):
		""" Convenience method that returns a new maturity with quote days all after date """
		return Maturity(self._expiration_date, [quote for quote in self._quotes if quote >= date_])

	def quote_for_days_before(self, days_before):
		""" Finds the nearest quote to the days out delta provided for this maturity. """

		date_looking_for = self._expiration_date - datetime.timedelta(days_before, 0, 0)
		target_quote = find_nearest_of(date_looking_for, self._quotes, lambda x: x.quote_date())
		return target_quote

	def days_out(self, quote):
		""" Returns the number of days before expiration this quote takes place """
		#TODO: assert that quote has same expiration date
		return self._expiration_date - quote.quote_date() 

	def with_contiguous_quotes(self):
		""" Returns a new maturity made up only of quotes that exist from the earliest quote to the end """

		return self

		first_date = self._quotes[0].quote_date()
		optiondays_available_first = set([quote.option_name for quote in self._quotes[0]])
		optiondays_available_last = set([quote.option_name for quote in self._quotes[-1]])
		quotes_available = optiondays_available_first.intersection(optiondays_available_last)

		##print "making new maturity" 

	#	if len(quotes_available) == 0:
			##print self._quotes[-1].quote_date(), self._quotes[-1].expiration_date(), self._quotes[0].quote_date(), self._quotes[-1].expiration_date(), self.expiration_date()
			#print sorted(optiondays_available_first)
			#print sorted(optiondays_available_last)

		new_quotes = []
		for quote in self._quotes:
			#print "per option", len(quote), len(quotes_available), len(optiondays_available_first), len(optiondays_available_last)
			new_quotes.append(make_quote_from_options(quote.quote_date(), [optionsday for optionsday in quote if optionsday.option_name in quotes_available]))

		#print len(self._quotes), len(new_quotes)

		#should have same number of quotes every day?

	#	for quote in new_quotes:
			#print len([q for q in quote]),

		#print "making maturity"

		return Maturity(self.expiration_date(), new_quotes)

	#TODO: should be a global in the same namespace
	def quote_on_expiration(self):
		return self.quote_for_days_before(0)


	def __iter__(self):
		return iter(self._quotes)

	def expiration_date(self):
		return self._expiration_date

	def __getitem__(self, index):
		#TODO: support quote date indecies as well
		return self._quotes[index]
	
class Chain(object):
	""" A collection of all maturities for a particular stock """
	def __init__(self, maturities):
		#TODO: assert that stock symbol is equal for all stocks
		#TODO: sort maturities in order of experation date
		self._maturities = maturities

	def __iter__(self):
		return iter(self._maturities)

	def __len__(self):
		return len(self._maturities)

	def __getitem__(self, index):
		#TODO: get by expiration date
		return self._maturities[index]

	def expires_before(self, date_):
		""" Creates a new options chain consisting only of maturities that expire before date_ """
		return Chain([maturity for maturity in self._maturities if maturity.expiration_date() <= date_])

def find_option(options, opt):
	opt = [x for x in options if x.option_name == opt.option_name]
	if len(opt) != 1:
		raise Exception("option not found")
	return opt[0]

def options_date_iterator(chain, start_date, target_date):
	""" Chain is a list of options all with the same expiration date, but different quote dates. Target date is a date
	    return an iterator that returns a pair - a date, and options chain - for every quote date in order """

    	by_quote_date = sorted(chain, key=OptionsDay.quote_date)
	return [(k, make_quote(list(g))) for (k,g) in itertools.groupby(by_quote_date, key=OptionsDay.quote_date) if start_date <= k <= target_date]

def condor_experiment(chain, body_spread, wingspan, days_out):
	results = []

	#last quote date of last maturity
	last_date = chain[-1][-1].quote_date()
	chain = chain.expires_before(last_date)

	errors = [] 

	print "Starting to find iron condors"
	for maturity_ in chain:
		#TODO: add in trading costs. $1 per option (remember an option is on 100 shares, so its 1 cent per share) plus $10 per trade, which may be as little as 1 cent per option on average.
		#pretty sure above is done?

		maturity = maturity_.with_contiguous_quotes()
		begining_quote = maturity.quote_for_days_before(days_out)
		
		#needs to be within 3 days
		if abs(maturity.days_out(begining_quote).days - days_out) > 4:
			errors.append(DateException(begining_quote.quote_date(), maturity.expiration_date() - datetime.timedelta(days_out), maturity.expiration_date()))
			continue

		last_index_price = begining_quote.underlying_price()

		try:
			ic = make_short_iron_condor(begining_quote, last_index_price, body_spread, wingspan)
		except ModelException as ex:
			errors.append(ex)
			continue
		#get nearest quote to expiration
		target_quote = maturity.quote_on_expiration()

		eic = next((ic.exit_value(quote) for quote in maturity.with_quotes_after(begining_quote) if ic.exit_position(quote)), ic.exit_value(maturity.quote_on_expiration()))

		#eic = ic.find_equivalent(target_quote)

		assert eic.exercise_value() + ic.holding_credit() >= -wingspan, "should not risk more than wingspan with {0} exercise, {1} holding and {2} wingspan".format(str(eic.exercise_value()),
																					   str(ic.holding_credit()),
																				   str(-wingspan))
		results.append(Result(ic, eic, wingspan))

	assert len(results) + len(errors) == len(chain)
	return (results, errors)

#We own 100 shares of SPY
#On a repeating cycle, sell 1 call that is 5% out of the money and expires in about 3-4 weeks. 
#If call expires worthless, you collect the premium and sell another one under same criteria (5% out of money on new price of SPY)
#If call expires in the money, the SPY stock is called out from you and you are forced to sell it (at a 5% gain plus the premium of the SPY call you sold)
#We should build in a stop loss also, so that if any any time in the SPY drops 5%, we sell out of our long position and limit any more than 5% loss on that cycle.

#After model is built, you can optimize 
#1) time to expiration (which I can already predict will be about 3-4 weeks based on the way theta decay is priced into contracts)
#2) % out of the money to sell call, which should be generally tied to your stop loss
#3) regress against vix which should provide forecasting ifor #2

#start at buy in date, we purchase 100 shares of spy. don't count comissions as we pretend we already hold it
#at end, we either collect premium because option is out of the money
#or option is in the money, in which case we sell spy at 5% premium, + option premium
#check stop loss *daily* until expiration, stop loss is at 5% and is matched with call %, if stop loss is triggered, exercise and only collect premium of option - loss. But we go all the way to expiration still
def theta_experiment(chain, days_out, call_spread, stop_loss):

	results = []

	#last quote date of last maturity
	last_date = chain[-1][-1].quote_date()
	chain = chain.expires_before(last_date)

	errors = [] 

	print "Starting to find covered calls"
	for maturity in chain:
		begining_quote = maturity.quote_for_days_before(days_out)

		#TODO: figure out an estimate for value of things that have errors so i can compare averages with errors included as a robustness analysis / sensitivity
		#needs to be within 4 days
		if abs(maturity.days_out(begining_quote).days - days_out) > 4:
			errors.append(DateException(begining_quote.quote_date(), maturity.expiration_date() - datetime.timedelta(days_out), maturity.expiration_date()))
			continue

		#TODO: add in trading costs. $1 per option (remember an option is on 100 shares, so its 1 cent per share) plus $10 per trade, which may be as little as 1 cent per option on average.
		try:
			cc = make_covered_call(begining_quote, call_spread, stop_loss)
		except ModelException as ex:
			errors.append(ex)
			continue

		#TODO: instead of adding the reason to cc, create an actual reason object ("called out", "stopped out" and "expired" perhaps?) and pair the covered call with 
		#the reason
		quotes_of_interest = maturity.with_quotes_after(begining_quote) # [quote for quote in maturity if begining_quote <= quote]
		cc.set_reason(next((cc.exit_value(quote) for quote in maturity.with_quotes_after(begining_quote) if cc.exit_position(quote)), cc.exit_value(maturity.quote_on_expiration())))
		results.append(cc)

	assert len(results) != 0
	return results, errors

class CoveredCall(object):
	def __init__(self, index_price, call, stop_loss):
		self.index_price = index_price
		self.call = call
		self.stop_loss = stop_loss
		#set up initial position as selling the call (take the bid) and a long position in the stock. pay only comissions on the option

	def called_out(self, quote):
		index_price = quote.underlying_price()
		return self.call.in_the_money_at(quote.underlying_price())

	#comission to buy or sell an option is 1 cent
	#comission to buy or sell a share of stock is roughly 1.7 cents
	#we calculate the latter by assuming 20% of our portfolio in the stock, and a 500K min portfolio, for a 100K share of stock
	#we can buy that whole thing at an average price of 160, netting ~600 shares (625). At $10 dollars a trade, that works out to 1.66 cents a share

	#TODO: need to estimate dividend yield during the holding period

	def option_comission(self):
		return .01

	def stock_comission(self):
		return .017

	def dividends_for(self, days, stock_price):
		assert days > 0
		div = stock_price * (pow(self.daily_dividend_yield(), days) - 1.0)
		assert div > 0
		return div

	def daily_dividend_yield(self):
		#we're assuming 2% per anum
		return pow(1.02, 1.0 / 365.0)

	def calculate_called_out_value(self, quote):

		days_held = days_between(quote, self.call)

		if not self.called_out(quote):
			return None

		#growth in spy

		self.capital_gains = self.call.strike() - self.call.last_symbol_price

		#premium on call
		premium = self.call.bid
		self.dividends = self.dividends_for(days_held, quote.underlying_price())
		
		#will need to pay comissions on the sell of the call, then the exercise of the call
		comissions = self.option_comission() + self.stock_comission()
		return (self.capital_gains + premium - comissions + self.dividends, "called out", (quote.underlying_price(), quote.quote_date()))

	def set_reason(self, reason):
		self.value = reason[0]
		self.reason = reason[1]
		self.reason_deets = reason[2]

	def exit_position(self, quote):
		return self.called_out(quote) or self.stopped_out(quote)

	def exit_value(self, quote):
		if self.called_out(quote):
			return self.calculate_called_out_value(quote)
		if self.stopped_out(quote):
			return self.calculate_stopped_out_value(quote)
		return self.calculate_exercise_value(quote)

	def stopped_out(self, quote):
		index_price = quote.underlying_price()
		return index_price < ((1.0 - self.stop_loss) * self.index_price)

	def calculate_stopped_out_value(self, quote):

		days_held = days_between(quote, self.call)

		if not self.stopped_out(quote):
			return None

		#shrinkage in spy
		self.capital_gains = quote.underlying_price() - self.index_price

		#will need to pay 2x comissions, one to sell spy and the other to buy it again at next cycle
		#and one on the sell of the call

		#comission to sell the call, buy it back, sell the stock, and buy it back
		comissions = (2 * self.option_comission()) + (2 * self.stock_comission())

		#TODO: it'd be more accurate if we did an average of the begining stock price and ending
		self.dividends = self.dividends_for(days_held, quote.underlying_price())
		
		opt = find_option(quote.calls, self.call)

		#buy back the options
		premium = self.call.bid - opt.ask
	
		return (self.capital_gains + premium - comissions + self.dividends, "stopped out", (quote.underlying_price(), quote.quote_date(), opt))

	def calculate_exercise_value(self, chain):

		days_held = days_between(chain, self.call)

		#growth or shrinkage in spy
		self.capital_gains = chain.calls[0].last_symbol_price - self.index_price

		#premium on call
		premium = self.call.bid

		#comission on the sell of the call
		comissions = self.option_comission()
		self.dividends = self.dividends_for(days_held, chain.calls[0].last_symbol_price)
		
		return (self.capital_gains+premium - comissions + self.dividends, "expired", (chain.calls[0].last_symbol_price, chain.calls[0].quote_date()))

	def risked(self):
		#what money we had to put up - basically the money to buy the stock
		return self.call.last_symbol_price + self.stock_comission()

	def premium(self):
		return self.value

	def return_(self):
		return (self.risked() + self.premium()) / self.risked()

	def quote_date(self):
		return self.call.quote_date()

	def expiration_date(self):
		return self.call.expiration_date()

	def is_win(self):
		return self.premium() > 0.0

	def is_loss(self):
		return self.premium() <= 0.0

	def holding_premium(self):
		return self.call.bid

	def __repr__(self):
		return str(self)

	def __str__(self):
		return ("Trade Date: {0}\n"
			"Expiration Date: {1}\n"
			"Open spy: {2}\n"
			"Call sold at: {3}\n"
			"Exit strategy: {4}\n"
			"With value of: {5}\n"
			"Consisting of cap gains: {6}\n"
			"And option premium: {7}\n"
			"And dividends: {8}\n"
			"Spy at: {9}\n"
			"On date: {10}\n"
			"For total risked of: {11}\n"
			"And return of {12}").format(str(self.quote_date()),
					            str(self.expiration_date()),
						    str(self.call.last_symbol_price),
						    str(self.call),
						    str(self.reason),
						    str(self.premium()),
						    str(self.capital_gains),
						    str(self.call.bid if self.reason!="stopped out" else self.call.bid - self.reason_deets[2].ask),
						    str(self.dividends),
						    str(self.reason_deets[0]),
						    str(self.reason_deets[1]),
						    str(self.risked()),
						    str(self.return_()))

def highest_bid(opts):
	""" Returns the option with the best bid price """
	return max(opts, key= lambda x: x.bid)

def make_covered_call(quote, call_spread, stop_loss):
	#TODO: move these assertions to Quote
	assert len(set([x.quote_date() for x in quote.calls])) == 1, "Should only have one quote date for all options in quote"
	assert len(set([x.expiration_date() for x in quote.calls])) == 1, "Should have only one expiration date for all options in quote"
	assert len(set([x.quote_date() for x in quote.puts])) == 1, "Should only have one quote date for all options in quote"
	assert len(set([x.expiration_date() for x in quote.puts])) == 1, "Should have only one expiration date for all options in quote"
	
	#TODO: this should also be enforced by quote
	calls = sorted(quote.calls, key=OptionsDay.strike)

	#TODO: move to quote
	#we find the nearest to, rather than the nearest under or nearest above
	target_call = find_nearest_of((1.0 + call_spread) * quote.underlying_price(), calls, key=OptionsDay.strike, on_tie=highest_bid)

	#TODO:check that the found call is within some tolerance or reject the play
	return CoveredCall(quote.underlying_price(), target_call, stop_loss)

def upper_quartile(data):
	#TODO: look into numpy.percentile
	#TODO: does this need to be sorted?
	sdata = sorted(data)
    	return numpy.median(sdata[len(sdata)/2:])

def intra_quartile_range(data):
    sdata = sorted(data)
    lower_quartile = numpy.median(sdata[:len(sdata)/2])
    return upper_quartile(data) - lower_quartile

def reject_upper_outliers(data, key):
    axis = [key(d) for d in data]
    out_of_range = upper_quartile(axis) + intra_quartile_range(axis)
    return [d for d in data if key(d) <= out_of_range]

#TODO: refactor common interface on a result class
def by_expiration_date(itm):
	return itm.expiration_date()

def get_return(itm):
	return itm.return_()

def get_premium(itm):
	return itm.premium()

def get_risked(itm):
	return itm.risked()

def make_summary_with_error(results, errors):
	#TODO: could turn a collection of results into its own object and put these on as attributes.
	#dict -> object
	#TODO: find common structure between results and inherit from that or reuse it
	#results.sort(key=Result.expiration_date)
	results.sort(key=by_expiration_date)
	summary_statistics = {}
	summary_statistics["num_results"] = len(results)
	summary_statistics["avg_abs_return"] = numpy.mean([x.premium() for x in results]) 
	summary_statistics["avg_return"] = numpy.mean([x.return_() for x in results]) 

	wins = [x.return_() for x in results if x.is_win()]
	losses = [x.return_() for x in results if not x.is_win()]

	summary_statistics["avg_win"] = numpy.mean(wins) if len(wins) != 0 else 0.0
	summary_statistics["avg_return_no_outliers"] = numpy.mean([x.return_() for x in reject_upper_outliers(results, get_return)])
	summary_statistics["avg_loss"] = numpy.mean(losses) if len(losses) != 0 else 0.0
	summary_statistics["win_percent"] = float(len(wins)) / len(results)
	summary_statistics["loss_percent"] = float(len(losses)) / len(results)
	summary_statistics["max_drawdown"] = min(results, key=get_premium)
	summary_statistics["max_gain"] = max(results, key=get_premium) 
	summary_statistics["std dev premium"] = numpy.std([x.premium() for x in results])
	summary_statistics["std dev return"] = numpy.std([x.return_() for x in results])
	summary_statistics["median return"] = numpy.median([k.return_() for k in results])
	summary_statistics["absolute risked"] = numpy.mean([x.risked() for x in results])
	summary_statistics["absolute holding premium"] = numpy.mean([x.holding_premium() for x in results])

	#this should use the robust reject_upper_outliers function
	summary_statistics["performance 100k"] = zip([k.expiration_date() for k in results], performance_estimate(100000, [k.return_() for k in results]))
	summary_statistics["num_errors"] = len(errors)

	assert not is_nan(summary_statistics["win_percent"])
	assert not is_nan(summary_statistics["avg_win"])
	assert not is_nan(summary_statistics["loss_percent"])
	assert not is_nan(summary_statistics["avg_loss"])
	
	numpy.testing.assert_approx_equal(summary_statistics["win_percent"] + summary_statistics["loss_percent"], 1.0, err_msg="Percents should add up to 100")
	numpy.testing.assert_approx_equal(summary_statistics["win_percent"] * summary_statistics["avg_win"] + summary_statistics["loss_percent"] * summary_statistics["avg_loss"], summary_statistics["avg_return"])
	assert 1.0 - (summary_statistics["win_percent"] + summary_statistics["loss_percent"]) < 0.01, "Percents should add up to 100"
	assert (summary_statistics["win_percent"] * summary_statistics["avg_win"]) + (summary_statistics["loss_percent"] * summary_statistics["avg_loss"]) - summary_statistics["avg_return"] < 0.01, "Average return should equal win return plus loss return"

	return summary_statistics

def make_summary(results):
	return make_summary_with_error(results, [])

def by_expiration_date(itm):
	return itm.expiration_date()

def segregate_by_date(results):
	return [sorted(list(g), key=by_expiration_date) for _,g in itertools.groupby(sorted(results, key=by_expiration_date), lambda k: k.expiration_date().year)]
	
def save_figure(ax_fig, directory):
	ax_fig[1].savefig(directory)
	ax_fig[1].clf()

def generate_figures(results, directory, title, decorator):

	if(not os.path.isdir(directory)):
		os.makedirs(directory)

	save_figure(histogram_of(results, get_premium, "Premiums for " + title + ", " + decorator, "Premiums"), directory + "/abs_histogram.png")
#	plt.show()
	save_figure(histogram_of(results, get_return, "Returns for " + title +", "+ decorator, "Returns"), directory + "/ret_histogram.png")
	save_figure(histogram_of(reject_upper_outliers(results, get_return), get_return, "Robust returns for " + title + ", " + decorator, "Robust Returns"), directory + "/rob_ret_histogram.png")
	save_figure(histogram_of(results, get_risked, "Dollars-at-Risk for " + title + ", " + decorator, "Dollars-at-Risk"), directory + "/risked_histogram.png")

	save_figure(time_series_of(results, get_premium, "Historical Premiums for " + title + ", " + decorator, "Premiums"), directory + "/abs_timeseries.png")

	save_figure(time_series_of(reject_upper_outliers(results, get_return), get_return, "Robust Historical Returns for " + title + ", " + decorator, "Robust Return"), directory + "/rob_ret_timeseries.png")
	save_figure(time_series_of(results, get_return, "Historical Returns for " + title + ", " + decorator, "Return"), directory + "/ret_timeseries.png")
	save_figure(performance_time_series(reject_upper_outliers(results, get_return), title, " 2008 - 2013"), directory + "/performance.png")

def save_results(results):
	""" Saves results out to a file for later audit """

	with open("figures/results.txt","w") as text_file:
		text_file.writelines(str(day) + "\n\n" for day in results)

def run_monte_carlo(returns):
	
	runs = 1000
	steps = 20

	results = []

	for run in range(runs):
		run_returns = [random.choice(returns) for _ in range(steps)]
		results.append(performance_estimate(100000, run_returns)[-1])

	save_figure(histogram(results, "Potential performance of $100,000 after 20 periods", "Value"), "monte_carlo_histogram.png")

def write_summary_file(results):
	summary = make_summary(results)

	print "Writing out summary file"
	summary_file = file("summary.txt","w")
	summary_file.write("Total summary:\n\n")
	summary_file.writelines(str(k) + ": " + str(v) + "\n" for k,v in summary.iteritems())
	summary_file.write("\n")

	yearly_summary = make_yearly_summary(results)

	for year in sorted(yearly_summary.iterkeys()):
		summary_file.write("For year: " + str(year) + "\n\n")
		summary_file.writelines(str(k) + ": " + str(v) + "\n" for k,v in yearly_summary[year].iteritems())
		summary_file.write("\n")

def make_yearly_summary(results):
	yearly_summary = {}
	seg_results = segregate_by_date(results)

	for year_ in seg_results:
		dt = year_[0].expiration_date().year
		yearly_summary[dt] = make_summary(year_)

	return yearly_summary

def save_all_figures(results, title):
	run_monte_carlo([x.return_() for x in reject_upper_outliers(results, get_return)])
	generate_figures(results, "figures", title, "2008-2013")

	seg_results = segregate_by_date(results)

	for year_ in seg_results:
		dt = year_[0].expiration_date().year
		generate_figures(year_, "figures/" + str(dt), title, str(dt))

def print_summary(f, arg_desc):
	def new_f(options, *args):
		results, error = f(options, *args)
		print "With parameters: "
		for arg in zip(arg_desc,args):
			print arg[0] + " " + str(arg[1])
		sum_ = make_summary(results)
		print "number of results " + str(sum_["num_results"])
		print "robust return " + str(sum_["avg_return_no_outliers"])
		return results, error
	return new_f	


def save_all_results(results, name):
	save_all_figures(results, name)
	write_summary_file(results)
	save_results(results)

def gen_time_results(options):

	days_out = 26 #3 weeks
	call_spread = .025
	stop_loss = .06

	results, error = theta_experiment(options, days_out, call_spread, stop_loss)

	summary = make_summary_with_error(results, error)

	assert summary["num_errors"] == 1
	assert summary["num_results"] == 15	
	assert summary["avg_return"] - 1.0096 < 0.001
	assert summary["std dev return"] - 0.0514 < 0.001
	assert results[0].expiration_date() == datetime.date(2008, 2, 16)
	assert len(results) == 15

	#BELOW IS FOR FULL OPTIONS ONLY
#	assert summary["num_errors"] == 0
#	assert summary["num_results"] == 92
#	assert summary["avg_return"] - 1.02147 < 0.001
#	assert summary["std dev return"] - 0.03226 < 0.001
#	assert results[0].expiration_date() == datetime.date(2008, 2, 16)
#	assert len(results) == 92 

	save_all_results(results, "Time Decay")
	return results

def gen_condor_results(options):
	#original, body spread 3%, wingspan 2, days out 14
	#first iteration, arbitrage on spreads allowed, body spread 3.5%, wingspan 1, days out 24
	#final iteration is wingspan of 3, body of 3% and days of 26

#initial
#	BODY_SPREAD = .03
#	WINGSPAN = 2
#	DAYS_OUT = 14

#optimized
	BODY_SPREAD = .03
	WINGSPAN = 3
	DAYS_OUT = 26

	results, error = condor_experiment(options, BODY_SPREAD, WINGSPAN, DAYS_OUT)

	save_all_results(results, "Iron Condor")

	print error
	print len(error)
	print len(results)

        summary = make_summary_with_error(results, error)

#	print summary
#	assert summary["num_errors"] == 2, str(summary["num_errors"]) + " should equal 2"  
#	print summary["num_errors"]
	#assert summary["num_results"] == 14

	assert_near  = numpy.testing.assert_approx_equal
	
	#full test
	assert_near(summary["avg_return"], 1.11795, 5, err_msg="Should have the same avg return")
	assert_near(summary["std dev return"], .70272, 5, err_msg="Should have same standard deviation")
	assert_near(summary["max_drawdown"].premium(), -2.28, 2, err_msg="Should have same max drawdown")
	assert len(results) == 89

	#partial test
#	assert_near(summary["avg_return"], 1.26492, 5, err_msg="Should have the same avg return")
#	print len(results), summary["std dev return"], summary["max_drawdown"], results[0].expiration_date()
#	assert_near(summary["std dev return"], .965233, 5, err_msg="Should have same standard deviation")
#	assert_near(summary["max_drawdown"].premium(), -1.93, 2, err_msg="Should have same max drawdown")


	assert results[0].expiration_date() == datetime.date(2008, 2, 16)
#	assert len(results) == 14

	return results

def optimize(options, function, args, is_good_result):

	optimization_results = []
	for parameters in args:
		results, error = function(options, *parameters)
		results = make_summary(results)
		if is_good_result(results):
			optimization_results.append([parameters, results["avg_return_no_outliers"]])

	return sorted(optimization_results, key=lambda x: x[1], reverse=True)

def gen_grid(options, function, args, is_good_result):
	
	optimization_results = []
	for parameters in args:
		results, error = function(options, *parameters)
		if is_good_result(results):
			optimization_results.append(results)

	return optimization_results 

def optimize_condor(options):
#	body_spread_range = numpy.arange(.005, .055, .005)
	body_spread_range = numpy.arange(.030, .035, .005)
	wingspan_range = numpy.arange(4, 6, 1)
	days_out_range = numpy.arange(25, 27, 1)
#	wingspan_range = numpy.arange(1, 6, 1)
#	days_out_range = numpy.arange(3, 32, 1)

	dec_experiment = print_summary(condor_experiment, ["body spread", "wingspan", "days out"])
	results = optimize(options, dec_experiment, itertools.product(body_spread_range, wingspan_range, [int(day) for day in days_out_range]), lambda x: 65 < x["num_results"] < 105)	

	for best_run in results[:10]:
		print "Max performance is: {0} with body spread of {1}, wingspan of {2} and days out of {3}".format(str(best_run[1]),
				 									            str(best_run[0][0]),
														    str(best_run[0][1]),
														    str(best_run[0][2]))
	return results		

def gen_condor_grid(options):
	body_spread_range = numpy.arange(.005, .055, .005)
	wingspan_range = numpy.arange(1, 6, 1)
	days_out_range = numpy.arange(3, 32, 1)

	dec_experiment = print_summary(condor_experiment, ["body spread", "wingspan", "days out"])

	#TODO: should probably weed out runs that have more errors than expected rather than fewer successes than expected.
	results = gen_grid(options, dec_experiment, itertools.product(body_spread_range, wingspan_range, [int(day) for day in days_out_range]), lambda x: True) #65 < len(x) < 105)	
	return results		

def sum_results(results):
	return [(r.days_out(), r.body_spread_goal(), r.wingspan(), r.quote_date(), r.expiration_date(), r.return_()) for r in results]

def optimize_time_premium(options):
	days_out_range = numpy.arange(3, 32, 1)
	call_spread_range = numpy.arange(.015, .105, .005)
	stop_loss_range = numpy.arange(.015, .105, .005)

	dec_experiment = print_summary(theta_experiment, ["days out", "call spread", "stop loss"])
	results = optimize(options, dec_experiment, itertools.product([int(day) for day in days_out_range], call_spread_range, stop_loss_range), lambda x: 85 < x["num_results"] < 110)

	for best_run in results[:10]:
		print "Max performance is: {0} with days out of {1}, call spread of {2} and stop loss of {3}".format(str(best_run[1]),
				 										     str(best_run[0][0]),
														     str(best_run[0][1]),
														     str(best_run[0][2]))
	return results

def main(options=None):

	if not options:
		print "Loading Options THIS IS EXPENSIVE"
#		options = load_options(test=True)
		options = load_options(test=False)

#	res = sum_results(list(itertools.chain.from_iterable(gen_condor_grid(options))))

#	write = csv.writer(open("iron_condor_results_cumulative.csv", "wb"))
#	write.writerow(["days_out", "body_spread", "wingspan", "quote_date", "expiration_date", "return"])
#	write.writerows(res)

#	return res

	return optimize_condor(options)
#	return gen_condor_results(options)
#	return gen_time_results(options)
#	return optimize_time_premium(options)

class Result:
	def __init__(self, begining_condor, expired_condor, wingspan):
		self._total_premium = begining_condor.holding_credit() + expired_condor.exercise_value()
		self._holding_premium = begining_condor.holding_credit()
		self._bear_call_lower = begining_condor.bear_call_lower
		self._bear_call_upper = begining_condor.bear_call_upper
		self._bull_put_upper = begining_condor.bull_put_upper
		self._bull_put_lower = begining_condor.bull_put_lower
		self._expired_bear_call_lower = expired_condor.bear_call_lower
		self._expired_bear_call_upper = expired_condor.bear_call_upper
		self._expired_bull_put_upper = expired_condor.bull_put_upper
		self._expired_bull_put_lower = expired_condor.bull_put_lower

		self._begining_condor = begining_condor
		self._expired_condor = expired_condor
		self._wingspan = wingspan

		assert self.risked() > 0.0, "Should have at least risked some money. {0} wingspan and {1} result".format(str(_wingspan), str(self))
	
		#TODO: how to express this? right now we need to put it in terms of a percent but we really can loose money due to comissions now?
		#two different ways of looking at return, possibly? 
		#assert self.return_() >= -0.03 #shouldn't have lost mroe than comissions
		
	def __repr__(self):
		return str(self)

	def __str__(self):
		return ("Trade Date: {0}\n"
		        "Short Positions: \n"
			"{1}\n"
			"{2} \n"
			"for total credit of\n"
			"Bid of short call {3} + Bid of short put {4} = {5}\n"
			"Long Positions: \n"
			"{6} \n"
			"{7} \n"
			"for cost of\n"
			"Ask of long call {8} + Ask of long short {9} = {10}\n"
			"Net credit of {11}\n"
			"At expiration, cover shorts:\n"
			"{12}\n"
			"{13}\n"
			"At cost of\n"
			"Exercise value of short call {14} + Exercise value of short put {15} = {16}\n"
			"And exercise longs:\n"
			"{17}\n"
			"{18}\n"
			"For benefit of\n"
			"Exercise value of long call {19} + Exercise value of long put {20} = {21}\n"
			"For total absolute return of position of {22}\n"
			"With capital required of {23} - {24} = {25}\n"
			"For relative return of {26}\n").format(str(self.quote_date()) #0
					                       ,str(self._bear_call_lower) #1
							       ,str(self._bull_put_upper) #2
							       ,str(self._bear_call_lower.bid) #3
							       ,str(self._bull_put_upper.bid) #4
							       ,str(self._bear_call_upper.bid + self._bull_put_upper.bid) #5
							       ,str(self._bear_call_upper) #6
							       ,str(self._bull_put_lower) #7
							       ,str(self._bear_call_upper.ask) #8
							       ,str(self._bull_put_lower.ask) #9
							       ,str(self._bear_call_upper.ask + self._bull_put_lower.ask) #10
							       ,str(self.holding_premium()) #11
							       ,str(self._expired_bear_call_lower) #12
							       ,str(self._expired_bull_put_upper) #13
							       ,str(self._expired_bear_call_lower.exercise_value()) #14
							       ,str(self._expired_bull_put_upper.exercise_value()) #15
							       ,str(self._expired_bear_call_lower.exercise_value() + self._expired_bull_put_upper.exercise_value()) #16
							       ,str(self._expired_bear_call_upper) #17
							       ,str(self._expired_bull_put_lower) #18
							       ,str(self._expired_bear_call_upper.exercise_value()) #19
							       ,str(self._expired_bull_put_lower.exercise_value()) #20
							       ,str(self._expired_bear_call_upper.exercise_value() + self._expired_bull_put_lower.exercise_value()) #21
							       ,str(self.premium()) #22
							       ,str(self._wingspan) #23
							       ,str(self.holding_premium()) #24
							       ,str(self.risked()) #25
							       ,str(self.return_())) #26  


	def return_(self):
		if(self.premium() + self.risked() < 0.0):
			print self.premium(), self.risked()
			assert False
		return (self.premium() + self.risked()) / self.risked()

	def risked(self):
		return self._wingspan - self._begining_condor.holding_credit() + .03 #risked wingspan minus the credit plus comissions

	def holding_premium(self):
		return self._begining_condor.holding_credit()
	
	def expiration_date(self):
		return self._begining_condor.expiration_date()

	def premium(self):
		return self._begining_condor.holding_credit() + self._expired_condor.exercise_value() - .03 #premium is credit minus comissions

	def is_win(self):
		return self.premium() >= 0.0

	def quote_date(self):
		return self._begining_condor.quote_date()

	def days_out(self):
		return (self.expiration_date() - self.quote_date()).days

	def body_spread_goal(self):
		return self._begining_condor.body_spread_goal()

	def wingspan(self):
		return self._wingspan

if __name__ == "__main__":
	main()	
