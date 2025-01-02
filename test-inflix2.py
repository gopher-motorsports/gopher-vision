def evaluate_infix(expression):
    print(expression)
    # Define operator precedence
    precedence = {"+": 1, "-": 1, "*": 2, "/": 2, "^": 3}
    operators = precedence.keys()

    def apply_operator(op, b, a):
        """Applies an operator to two operands and returns the result."""
        if op == "+":
            return a + b
        elif op == "-":
            return a - b
        elif op == "*":
            return a * b
        elif op == "/":
            if b == 0:
                return 0  # Avoid division by zero
            return a / b
        elif op == "^":
            return a ** b
        else:
            raise ValueError(f"Unknown operator: {op}")

    values = []  # Stack for numbers
    ops = []     # Stack for operators

    def precedence_of(op):
        # Returns the precedence of an operator
        return precedence[op] if op in precedence else 0

    i = 0
    while i < len(expression):
        token = expression[i]

        # If the token is a negative number (e.g., "-90.0466")
        if token.startswith("-") and token[1:].replace(".", "", 1).isdigit():
            values.append(float(token))  # Convert to float
        # If the token is a number (integer or float)
        elif token.replace(".", "", 1).isdigit():
            values.append(float(token))  # Convert to float
        elif token == "(":  # If token is a left parenthesis
            ops.append(token)
        elif token == ")":  # If token is a right parenthesis
            while ops and ops[-1] != "(":
                values.append(apply_operator(ops.pop(), values.pop(), values.pop()))
            ops.pop()  # Remove the "("
        elif token in operators:  # If token is an operator
            # Handle negative numbers (unary minus) by looking at the previous token
            if token == "-" and (i == 0 or expression[i - 1] in operators or expression[i - 1] == "("):
                # Treat it as a negative number
                i += 1
                token = "-" + expression[i]  # Combine with the next token
                values.append(float(token))
            else:
                # Handle precedence and associativity
                while (ops and ops[-1] != "(" and
                        precedence_of(ops[-1]) >= precedence_of(token)):
                    values.append(apply_operator(ops.pop(), values.pop(), values.pop()))
                ops.append(token)
        else:
            raise ValueError(f"Invalid token: {token}")

        i += 1

    # Apply remaining operators
    while ops:
        values.append(apply_operator(ops.pop(), values.pop(), values.pop()))

    return values[0]


expression = ['(', '0', '+', '-90.04664611816406', ')', '/', '4']
result = evaluate_infix(expression)
print(result)  # Output: -22.511661529541016