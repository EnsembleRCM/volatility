def performance_estimate(principle, returns):
	""" returns is a tuple of date and return for that date """

	results = []

	p = principle

	for raw_return in returns:
		safe_p = p * .8
		at_risk_p = p * .2
		at_risk_p *= raw_return
		p = at_risk_p + safe_p
		results.append(p)

	return results

