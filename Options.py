import utility
import datetime

class ModelException(Exception):
	pass

class OptionNotAvailableException(ModelException):
	def __init__(self, strikes):
		self.strikes = strikes

class ArbitrageException(ModelException):
	def __init__(self, position):
		self.position = position

class NoTradesFound(ModelException):
	def __init__(self, options_chain):
		self.options_chain = options_chain

class DateException(ModelException):
	def __init__(self, dates, target, for_expiration):
		self.dates = dates
		self.target = target
		self.for_expiration = for_expiration

	def __str__(self):
		return "Date Exception, first available quote at: " + str(self.dates) + ", but needed quote at " + str(self.target) + " for expiration " + str(self.for_expiration)

	def __repr__(self):
		return str(self)
				
class CallT(object):
	def exercise_value(self, underlying_price, strike):
		return max(0, underlying_price - strike)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "Call"

	def __eq__(self, other):
		return isinstance(other, CallT)

	def is_call(self):
		return True

	def is_put(self):
		return False

Call = CallT()


class PutT(object):
	def exercise_value(self, underlying_price, strike):
		return max(0, strike - underlying_price)

	def __repr__(self):
		return str(self)

	def __str__(self):
		return "Put"

	def __eq__(self, other):
		return isinstance(other, PutT)

	def is_call(self):
		return False

	def is_put(self):
		return True

Put = PutT()

class OptionsDay(object):
	__slots__ = ("option_name", "last_symbol_price", "options_type", "_expiration_date", "_quote_date", "_strike", "bid", "ask", "exchange", "volume", "open_interest")
	def __init__(self, option_name, last_symbol_price, options_type, expiration_date, quote_date, strike, bid, ask, exchange, volume, open_interest, *args):

#SO DO WE NEED TO JUST REPLACE THE FIRST THREE LETTERS WITH SPY? INTERESTING EXPERIMENT. JUST REPLACE FIRST 3 LETTERS WITH SPY AND THEN DO A UNIQUE ON ALL CODES. IF IT WORKS, THEN WE SHOULD HAVE NO DUPLICATES
#WE CAN ALSO THROW OUT EVERYTHING THAT ISN'T FROM ALL EXCHANGES? SEEMS LIKE A SAFE BET.

		self.option_name = option_name
		self.last_symbol_price = last_symbol_price
		self.options_type = options_type
		self._expiration_date = expiration_date
		self._quote_date = quote_date
		self._strike = strike
		self.bid = bid
		self.ask = ask
		self.exchange = exchange
		self.volume = volume
		self.open_interest = open_interest


	def exercise_value(self):
		return self.options_type.exercise_value(self.last_symbol_price, self.strike())

	def in_the_money(self):
		return self.exercise_value() > 0

	def in_the_money_at(self, value):
		return self.options_type.exercise_value(value, self.strike())

	def expiration_date(self):
		return self._expiration_date

	def quote_date(self):
		return self._quote_date

	def strike(self):
		return self._strike

	def __repr__(self):
		return str(self)

	def __eq__(self, other):
		return (self.last_symbol_price == other.last_symbol_price and
			self.options_type == other.options_type and
			self._expiration_date == other._expiration_date and
			self._quote_date == other._quote_date and
			self._strike == other._strike and
			self.bid == other.bid and
			self.ask == other.ask and
			self.exchange == other.exchange)
		

	def __str__(self):
		return ("{0} option\n"
		        "Expiration: {1}\n"
		        "Strike: {2}\n"
		        "Date: {3}\n"
	                "Bid(short): {4}\n"
		        "Ask(long): {5}\n"
		        "Underlying: {6}\n"
		        "{7} with value: {8}").format(self.options_type
 		 	                             ,self._expiration_date
                   				     ,self.strike()
						     ,self._quote_date
						     ,self.bid
						     ,self.ask
						     ,self.last_symbol_price
						     ,"In the money" if self.in_the_money() else "Out of the money"
						     ,self.exercise_value())
	
	def is_call(self):
		return self.options_type.is_call()

	def is_put(self):
		return self.options_type.is_put()

	def underlying_price(self):
		return self.last_symbol_price

Day = OptionsDay

def make_maturity_from_options(expiration_date, options):
	""" Builds a maturity data structure from a list of unsorted options with the same expiration date """
	assert(all([option.expiration_date() == expiration_date for option in options]))

	options = sorted(options, key=OptionsDay.quote_date)
	return Maturity(expiration_date, [make_quote_from_options(quote_date, options_) for quote_date, options_ in utility.sorted_groupby(options, OptionsDay.quote_date)])
#	return Maturity(expiration_date, sorted(options, key=OptionsDay.quote_date))

def make_quote_from_options(quote_date, options):
	assert all(opt.quote_date() == options[0].quote_date() for opt in options)
	assert all(opt.expiration_date() == options[0].expiration_date() for opt in options)

	#we want to eliminate duplicate strike prices and take * 
#	duplicates = sorted(find_duplicates(options, key=OptionsDay.strike), key=OptionsDay.strike)

#	for d in duplicates:
#		print d.option_name, d.exchange, d.quote_date(), d.expiration_date(), d.strike()

	return make_quote(options)

def make_quote_from_options(quote_date, options):
	assert all(opt.quote_date() == options[0].quote_date() for opt in options)
	assert all(opt.expiration_date() == options[0].expiration_date() for opt in options)

	#we want to eliminate duplicate strike prices and take * 
#	duplicates = sorted(find_duplicates(options, key=OptionsDay.strike), key=OptionsDay.strike)

#	for d in duplicates:
#		print d.option_name, d.exchange, d.quote_date(), d.expiration_date(), d.strike()


	return make_quote(options)

def take_average_quote(quotes):

	assert len(quotes) != 0

#	print [q.exchange for q in quotes]

	avg_exchange_quote = [quote for quote in quotes if quote.exchange == "*"]
	if len(avg_exchange_quote) == 0:
		print [(q.strike(), q.option_name, q.quote_date(), q.expiration_date()) for q in avg_exchange_quote]
		print quotes
		print [q.exchange for q in quotes]

		#this means that our 'average' quote isn't there. in this case, we take ? assuming it's average if its there

		avg_exchange_quote = [quote for quote in quotes if quote.exchange == "?"]
		if len(avg_exchange_quote) == 0:
			print quotes
			print [q.exchange for q in quotes]

			#this means average and unknown aren't there. in this case, we prefer "W" since it's the chicago board options exchange
			avg_exchange_quote = [quote for quote in quotes if quote.exchange == "W"]
			if len(avg_exchange_quote) == 0:
				#this means that average and unknown aren't there. in this case, we see if there's only one quote. we take that as the best estimate

#TODO: right here we should be averaging what's left.
#				if len(quotes) == 1:
				return quotes[0]
			else:
				return avg_exchange_quote[0]

		#TODO: we're actually returning the first of possible multiple ? quotes. we really need an actual average, 
		#but don't have one yet since we have to return a complete quote object
		return avg_exchange_quote[0]

	#TODO: same as above. not necessarily taking only one.
	return avg_exchange_quote[0]

def make_quote(options):
	calls = [x for x in options if x.is_call()]
	puts = [x for x in options if x.is_put()]

#	Note: For some reason, some chains have different numbers of calls than puts.
#	assert len(calls) == len(puts), "Calls and puts should have same number of strikes, but don't. Calls have " +  str(len(calls)) + " and puts have " + str(len(puts))
#	assert len(calls) != 0

	return Quote(sorted(calls, key=OptionsDay.strike), sorted(puts, key=OptionsDay.strike, reverse=True))

#TODO: rename this "daily quote". it's a group of options with the same expiration and quote date.
class Quote(object):
	""" All options that share the same quote date and expiration date. """
	def __init__(self, calls, puts):
		#TODO: assert that these all have the same underlying symbol 
		assert(all([cl.quote_date() == calls[0].quote_date() for cl in calls]))
		assert(all([pt.quote_date() == puts[0].quote_date() for pt in puts]))

		assert(all([call.expiration_date() == calls[0].expiration_date() for call in calls]))
		assert(all([put.expiration_date() == puts[0].expiration_date() for put in puts]))
		
		assert(all([call.underlying_price() == calls[0].underlying_price() for call in calls]))
		assert(all([put.underlying_price() == puts[0].underlying_price() for put in puts]))

		#TODO: want to go ahead and figure out a way to drop incomplete quotes
		#actually need to think about this. there are some quotes without calls or without puts. these seem worthless, but there
		#are others that simply have unequal, but not very, numbers of calls and puts?

		#print "in quote", len(calls), len(puts) 

		assert(calls[0].underlying_price() == puts[0].underlying_price() if len(calls) == len(puts) else True)

		self.calls = calls
		self.puts = puts

		self._expiration_date = calls[0].expiration_date() if len(calls) > 0 else puts[0].expiration_date()
		self._quote_date = self.calls[0].quote_date() if len(calls) > 0 else self.puts[0].quote_date()
		self._underlying_price = self.calls[0].underlying_price() if len(calls) > 0 else self.puts[0].underlying_price()

	def quote_date(self):
		return self._quote_date

	def call_at(self, strike):
		""" Returns the call at the passed in strike price """
		options = [c for c in self.calls if c.strike() == strike]

		if len(options) == 0:
			print "in options, no calls available at {0}".format(strike)
			raise OptionNotAvailableException(self)

		return options[0] if 1 == len(options) else take_average_quote(options)
#		return next(c for c in self.calls if c.strike() == strike)
#		bear_call_lower = find_nearest_of((1.0 + body_spread) * underlying_price, options_chain.calls, OptionsDay.strike, take_average_quote) 

#	try:
#		bear_call_upper = next(c for c in options_chain.calls if c.strike() == (bear_call_lower.strike() + wingspan)) 

	def put_at(self, strike):
		""" Returns the put at the passed in strike price """
	#	return next(c for c in self.puts if c.strike() == strike)
		options = [p for p in self.puts if p.strike() == strike]

		if len(options) == 0:
			print "in options, no puts available at {0}".format(strike)
			raise OptionNotAvailableException(self)

		return options[0] if 1 == len(options) else take_average_quote(options)

	def call_near(self, strike):
		""" Returns the call closest to the passed in strike price """
		return utility.find_nearest_of(strike, self.calls, OptionsDay.strike, take_average_quote) 

	def put_near(self, strike):
		""" Returns the put closest to the passed in strike price """
		return utility.find_nearest_of(strike, self.puts, OptionsDay.strike, take_average_quote) 

	def underlying_price(self):
		""" The price of the underlying stock this option is traded on. Technically, the close on this date. """
		return self._underlying_price

	def expiration_date(self):
		return self._expiration_date

	def __cmp__(self, other):
		return cmp(self.quote_date(), other.quote_date() if isinstance(other, Quote) else other)

	def __iter__(self):
		return iter(self.calls + self.puts)

	def __len__(self):
		return len(self.calls) + len(self.puts)

	def __getitem__(self, name):
		""" Gets an option by name """
		return next(optionsday for optionsday in iter(self) if optionsday.name() == name)

	def __repr__(self):
		str_ = "Calls\n"
		for opt in sorted(self.calls, key=OptionsDay.strike):
			str_ += "{0} {1} {2} {3} {4}\n".format(opt.strike(), opt.bid, opt.ask, opt.volume, opt.open_interest)

		str_ += "Puts\n"
		for opt in sorted(self.puts, key=OptionsDay.strike):
			str_ += "{0} {1} {2} {3} {4}\n".format(opt.strike(), opt.bid, opt.ask, opt.volume, opt.open_interest)

		return str_

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
		target_quote = utility.find_nearest_of(date_looking_for, self._quotes, lambda x: x.quote_date())
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


