import numpy as np
from scipy.stats import norm
from utils import nonnegative

class CFMM:
    def __init__(self, x, y, xbounds, ybounds, fee):
        self.x = x
        self.y = y
        self.xbounds = xbounds
        self.ybounds = ybounds
        self.gamma = 1 - fee


class UniV2(CFMM):
    def __init__(self, x, y, fee):
        super().__init__(x, y, np.inf, np.inf, fee)

    def TradingFunction(self):
        k = self.x * self.y
        return k

    def swapXforY(self, deltax):
        assert nonnegative(deltax)
        deltay = self.y - self.TradingFunction()/(self.x + self.gamma * deltax)
        assert nonnegative(deltay)
        self.x += deltax
        self.y -= deltay
        effective_price = deltay/deltax
        return deltay, effective_price

    def swapYforX(self, deltay):
        assert nonnegative(deltay)
        deltax = self.x - self.TradingFunction()/(self.y + self.gamma * deltay)
        assert nonnegative(deltax)
        self.y += deltay
        self.x -= deltax
        effective_price = deltay/deltax
        return deltax, effective_price

    def getMarginalPriceAfterXTrade(self, deltax, numeraire):
        assert nonnegative(deltax)
        assert numeraire == 'y' or numeraire == 'x'
        if numeraire == 'y':
            return self.gamma*self.TradingFunction()/(self.x + self.gamma*deltax)**2
        elif numeraire == 'x':
            return 1/self.gamma*self.TradingFunction()/(self.x + self.gamma*deltax)**2

    def getMarginalPriceAfterYTrade(self, deltay, numeraire):
        assert nonnegative(deltay)
        assert numeraire == 'y' or numeraire == 'x'
        if numeraire == 'y':
            return 1/(self.gamma*self.TradingFunction()/(self.y + self.gamma*deltay)**2)
        elif numeraire == 'x':
            return self.gamma*self.TradingFunction()/(self.y + self.gamma*deltay)**2

    def findArbitrageAmountYIn(self, m):
        '''
        Given a reference price denominated in y, find the amount of y to swap in
        in order to align the price of the pool with the reference market.
        '''
        assert m > self.getMarginalPriceAfterYTrade(0, "y")
        def inverseG(price):
            return np.sqrt(self.TradingFunction()/price) - self.y
        # print("inverG", inverseG(1/m))
        # For this inverG formula, the target price must be in x.y-1
        m = 1/m
        return (1/self.gamma)*inverseG(m/self.gamma)

    def findArbitrageAmountXIn(self, m):
        '''
        Given a reference price denominated in y, find the amount of x to swap in
        in order to align the price of the pool with the reference market.
        '''
        assert m < self.getMarginalPriceAfterXTrade(0, "y")
        def inverseG(price):
            return np.sqrt(self.TradingFunction()/price) - self.x
        print("inverG", inverseG(m))
        return (1/self.gamma)*inverseG(m/self.gamma)


    class RMM01(CFMM):
        def __init__(self, x, y, fee, strike, vol, duration, env, timescale):
            super().__init__(x, y, 1, np.inf, fee)
            self.K = strike
            self.v = vol
            self.T = duration
            self.env = env
            self.timescale

        def TradingFunction(self):
            tau = self.T - self.timescale*self.env.now
            k = self.y - self.K*norm.cdf(norm.ppf(1-self.x)-self.v*np.sqrt(tau))
            return k