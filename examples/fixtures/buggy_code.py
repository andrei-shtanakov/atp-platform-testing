"""Module with intentional bugs for testing code review agents."""


def calculate_average(numbers):
    """Calculate the average of a list of numbers."""
    # Bug 1: No check for empty list (ZeroDivisionError)
    total = sum(numbers)
    return total / len(numbers)


def find_max(lst):
    """Find the maximum value in a list."""
    # Bug 2: Initializing with 0 fails for all-negative lists
    max_val = 0
    for item in lst:
        if item > max_val:
            max_val = item
    return max_val


def merge_dicts(a, b):
    """Merge two dictionaries."""
    # Bug 3: Mutates the original dict 'a'
    result = a
    result.update(b)
    return result


def safe_divide(a, b):
    """Divide a by b safely."""
    # Bug 4: Catches too broad exception, hides real errors
    try:
        return a / b
    except Exception:
        return 0


def process_items(items):
    """Double positive items, divide negative by zero."""
    results = []
    for i in range(len(items)):
        if items[i] > 0:
            results.append(items[i] * 2)
        else:
            # Bug 5: Division by zero for non-positive items
            results.append(items[i] / 0)
    return results


def remove_duplicates(lst):
    """Remove duplicates while preserving order."""
    # Bug 6: Uses set() which doesn't preserve order in older Python
    # Also loses original list's order guarantee
    return list(set(lst))


class UserManager:
    """Manage users."""

    users = []  # Bug 7: Mutable class variable shared across instances

    def add_user(self, name):
        self.users.append(name)

    def get_users(self):
        return self.users
