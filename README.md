# Kalshi trading bot

This repository contains an experimental trading bot

## Why is it open-source?

I'm not super optimistic about getting this trading bot to be profitable, so far 
I have not run it consistently enough to show sustained profits. If that is ever
the case, I will probably make the repo private, but until that time, it's more
of a fun project that may spark some conversations with people.

## Overview

I am trying a bunch of different strategies. Here are some strategies I have or
plan to investigate. I am giving each random names that make sense to me even
though there are probably much smarter quant people than me who know what to actually
call them

### Swing trading
**Hyopothesis**: Traders overreact to recent information and tend to overindex on 
whichever bracket the financial instruments are currently in. If this is the case,
then there should be money to be made buying highest probability bracket (no) and waiting
for it to swing to a different one.

### Instrinsic value
**Hypothesis**: The price predictions will deviate from previous statistical likelihoods. 
If we use historical S&P volatililty to compute the likelhiood of price movements
we can buy yes when the market is "undervaluing" certain brackets and buy no when
the market is overvaluing certain brackets

## Infrastructure
Currently, the trading bot is living on an EC2 instance that starts up at the 
beginning of each trading day. There are python scripts scheduled with cron to 
run at regular intervals.