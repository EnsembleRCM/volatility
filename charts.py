import matplotlib.pyplot as plt
import numpy
import matplotlib.dates as mdates
from analysis import *

def histogram(data, name, xlabel):
	fig = plt.figure(name)
	ax = fig.add_subplot(1,1,1)
	n, bins, patches = ax.hist(data, 30, normed=True, facecolor='green', alpha=.75)
	ax.set_xlabel(xlabel)
	ax.set_title(name)
	ax.grid(True)
	return ax, fig

def histogram_of(results, key, title, xlabel):
	return histogram([key(x) for x in results], title, xlabel)

def time_series(data, dates, title, ylabel):
	fig = plt.figure(title)
	ax = fig.add_subplot(1,1,1)
	ax.plot_date(x=dates, y=data, fmt="r-")
	ax.set_title(title)
	ax.set_ylabel(ylabel)
	ax.set_xlabel("Date")
	ax.grid(True)
	return ax, fig

def time_series_of(results, key, title, xlabel):
	values = numpy.array([key(x) for x in results])
	dates = numpy.array([mdates.date2num(x.expiration_date()) for x in results])

	return time_series(values, dates, title, xlabel)

def performance_time_series(results, title, decorator):
	returns = numpy.array(performance_estimate(100000, [k.return_() for k in results]))
	dates = numpy.array([mdates.date2num(k.expiration_date()) for k in results])

	return time_series(returns, dates, "Performance of $100,000 using " + title + ", " + decorator, "Value")

