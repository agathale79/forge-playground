"""calculator: a minimal, stdlib-only arithmetic expression evaluator.

Expressions are scanned, parsed by a recursive-descent parser into a
postfix (RPN) program, and evaluated by an iterative stack machine.
No use is made of eval, exec, compile, ast or re.
"""

__version__ = "0.1.0"
