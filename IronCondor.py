import Options

def make_short_iron_condor(options_chain, underlying_price, body_spread, wingspan):
	#we assume closest rather than closest above or closest below
	#TODO: need better on tie behavior!

	if(body_spread > 0.10):
		print "Warning, body spread is expecting a 0.0 to 1.0 percentage, received {0}!".format(body_spread)

	if len(options_chain.calls) == 0:
		print "no calls"
		raise Options.OptionNotAvailableException(options_chain)

	bear_call_lower = options_chain.call_near((1.0 + body_spread) * underlying_price)

	try:
		bear_call_upper = options_chain.call_at(bear_call_lower.strike() + wingspan)
	except StopIteration:
		print "ran out of calls for bear call upper, needed {0}".format(bear_call_lower.strike() + wingspan)
		raise Options.OptionNotAvailableException(options_chain)

	#TODO: need better on_tie behavior!

	bull_put_upper = options_chain.put_near((1.0 - body_spread) * underlying_price)

	try:
		bull_put_lower = options_chain.put_at(bull_put_upper.strike() - wingspan)
	except StopIteration:
		print "ran out of calls for bull put lower, needed {0}".format(bull_put_upper.strike() - wingspan)
		raise Options.OptionNotAvailableException(options_chain)
	
	if(bull_put_upper.bid < 0.001 or bull_put_lower.ask < 0.001 or bear_call_lower.bid < 0.001 or bear_call_upper.ask < 0.001):
		raise Options.NoTradesFound(options_chain)
		#errors.append(("No trades today.", (bull_put_upper.bid, bull-put_lower.ask, bear_call_lower.bid, bear_call_upper.ask, bull_put_upper.expiration_date())))

	sic = ShortIronCondor(bear_call_lower, bear_call_upper, bull_put_upper, bull_put_lower, wingspan, body_spread)
	if(sic.holding_credit() >= wingspan or sic.holding_credit() < 0.0):
		raise ArbitrageException(sic)
	if(sic.bull_put_upper.bid - sic.bull_put_lower.ask >= wingspan):
		raise ArbitrageException(sic)
	if(sic.bear_call_lower.bid - sic.bear_call_upper.ask >= wingspan):
		raise ArbitrageException(sic)

	return sic

class ShortIronCondor(object):
	def __init__(self, bear_call_lower, bear_call_upper, bull_put_upper, bull_put_lower, wingspan, body_spread_goal):
		self.bear_call_lower = bear_call_lower
		self.bear_call_upper = bear_call_upper
		self.bull_put_upper = bull_put_upper
		self.bull_put_lower = bull_put_lower
		self._wingspan = wingspan
		self._body_spread_goal = body_spread_goal
		
		assert bear_call_lower.quote_date() == bear_call_upper.quote_date() == bull_put_upper.quote_date() == bull_put_lower.quote_date()
		assert bear_call_lower.expiration_date() == bear_call_upper.expiration_date() == bull_put_upper.expiration_date() == bull_put_lower.expiration_date()

	def find_equivalent(self, options_chain):
		#TODO: can't just look for strikes! have to look for equivalent names!
		expired_bear_call_lower = options_chain.call_at(self.bear_call_lower.strike())
		expired_bear_call_upper = options_chain.call_at(self.bear_call_upper.strike())
		expired_bull_put_lower = options_chain.put_at(self.bull_put_lower.strike())
		expired_bull_put_upper = options_chain.put_at(self.bull_put_upper.strike())

		#expired_bear_call_lower = next(c for c in options_chain.calls if c.strike() == self.bear_call_lower.strike())
		#expired_bear_call_upper = next(c for c in options_chain.calls if c.strike() == self.bear_call_upper.strike())
		#expired_bull_put_lower = next(c for c in options_chain.puts if c.strike() == self.bull_put_lower.strike())
		#expired_bull_put_upper = next(c for c in options_chain.puts if c.strike() == self.bull_put_upper.strike())

		#TODO: can't find equivalent names? needed for correct stop loss
#		expired_bear_call_lower = next(c for c in options_chain.calls if c.option_name == self.bear_call_lower.option_name)
#		expired_bear_call_upper = next(c for c in options_chain.calls if c.option_name == self.bear_call_upper.option_name)
#		expired_bull_put_lower = next(c for c in options_chain.puts if c.option_name == self.bull_put_lower.option_name)
#		expired_bull_put_upper = next(c for c in options_chain.puts if c.option_name == self.bull_put_upper.option_name)


		sic = ShortIronCondor(expired_bear_call_lower, expired_bear_call_upper, expired_bull_put_upper, expired_bull_put_lower, self._wingspan, self._body_spread_goal)
		assert sic.expiration_date() == self.expiration_date()
		return sic

	def holding_credit(self):
		#TODO: should there always be a credit for the spread? or should we change behavior based on whether or not there's a credit for the spread?
		#assert put_spread_holding_premium >= 0, str(bull_put_upper.bid) + " " + str(bull_put_lower.ask) + " " + str(expiration_date)
		#assert call_spread_holding_premium >= 0, str(bear_call_lower.bid) + " " + str(bear_call_upper.ask) + " " + str(expiration_date)
		put_spread_holding_premium = self.bull_put_upper.bid - self.bull_put_lower.ask
		call_spread_holding_premium = self.bear_call_lower.bid - self.bear_call_upper.ask
		return put_spread_holding_premium + call_spread_holding_premium

	def exit_position(self, quote):
#		if Result(self, self.find_equivalent(quote), self
		return False
		#This is where a stop loss calculation could go, however, no stop loss makes sense for iron condors. I tried all the way down to 60% ( < .4) stop loss.
		#TODO: idea, put in a stop win? exit on return over 10%? 20%? also, move down past 60% all the way to 0% to prove stop losses don't work.
	#	return Result(self, self.find_equivalent(quote), self.wingspan).return_() < .4

	def exit_value(self, quote):
		return self.find_equivalent(quote)

	def exercise_value(self):
		#sell our long positions
		bear_call_upper_premium = self.bear_call_upper.exercise_value()
		bull_put_lower_premium = self.bull_put_lower.exercise_value()

		#close our short positions
		bear_call_lower_premium = -self.bear_call_lower.exercise_value()
		bull_put_upper_premium = -self.bull_put_upper.exercise_value()
		return bear_call_upper_premium + bull_put_lower_premium + bear_call_lower_premium + bull_put_upper_premium

	def expiration_date(self):
		return self.bear_call_lower.expiration_date()

	def quote_date(self):
		return self.bear_call_lower.quote_date()

	def days_out(self):
		return (self.expiration_date() - self.quote_date()).days

	def body_spread_goal(self):
		return self._body_spread_goal

	def wingspan(self):
		return self._wingspan

	def max_return(self):
		""" The maximum return this spread could achieve """
		return self.holding_credit() / self.required_capital()


	def required_capital(self):
		#this isn't required capital, but instead the capital i'll have in reserve that's subject to risk free rate
		#required capital is pt spread - the expected value of the other wing, or max of the wingspan
		return self._wingspan - self.holding_credit()

	def __eq__(self, rhs):
		return (self.bear_call_lower == rhs.bear_call_lower and
	                self.bear_call_upper == rhs.bear_call_upper and
			self.bull_put_upper == rhs.bull_put_upper and
			self.bull_put_lower == rhs.bull_put_lower and
			self._wingspan == rhs._wingspan)


