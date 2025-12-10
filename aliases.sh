#!/bin/bash
# 키움증권 트레이딩 봇 aliases

alias aa='python /e/amazonq/trading_bot.py'
alias gs='git status'
alias gd='git diff'
alias ga='git add'
alias gc='git commit --amend'
alias gp='git push origin main'
alias gv='git branch -vv'
alias trading='python /e/amazonq/trading_bot.py'
alias strategy1='python /e/amazonq/trading_bot.py --strategy=1'
alias strategy2='python /e/amazonq/trading_bot.py --strategy=2'

# 사용법:
# source /e/amazonq/aliases.sh
# trading      # 기본 전략으로 실행
# strategy1    # 볼린저밴드 전략
# strategy2    # RSI 전략
