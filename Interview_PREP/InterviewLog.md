# VoerEir [19/04/2024] [Python, Linux, MySQL]

## Difference betweeen tuple, list and set.

**Tuple**:
- Tuples are immutable sequences, meaning once created, their elements cannot be changed.
- They are defined using parentheses `()`.
- Tuples are often used to represent fixed collections of items, such as coordinates or settings.
- Example: `coordinates = (3, 4)`

**List**:
- Lists are mutable sequences, allowing for modification after creation.
- They are defined using square brackets `[]`.
- Lists are versatile and commonly used for storing collections of similar items.
- Example: `numbers = [1, 2, 3, 4, 5]`

**Set**:
- Sets are unordered collections of unique elements.
- They are defined using curly braces `{}` or by using the `set()` constructor.
- Sets are useful for operations like testing membership and eliminating duplicates.
- Example: `unique_numbers = {1, 2, 3, 4, 5}`

**Differences**:
- **Mutability**: Tuples are immutable, while lists are mutable. Sets are mutable but their elements are immutable and unordered.
- **Order**: Lists and tuples maintain the order of elements as they are inserted, while sets do not guarantee any specific order.
- **Duplication**: Tuples and lists can contain duplicate elements, while sets automatically eliminate duplicates.
- **Membership Testing and Operations**: Sets are particularly efficient for testing membership and performing set operations like intersection, union, and difference.

## Why list can't be the key of an dictionary?
In Python, dictionary keys must be hashable, meaning they must be immutable and have a hash value that doesn't change over time. Lists, being mutable, cannot be used as dictionary keys because they cannot guarantee these properties.

Here's why lists cannot be dictionary keys:

1. **Mutability**: Lists are mutable, meaning their elements can be changed after creation. If a list were used as a key in a dictionary and its contents were modified, it would lead to inconsistencies and errors in the dictionary.

2. **Hashability**: Dictionary keys must be hashable, which means they must have a hash value that remains constant throughout their lifetime. Since lists can be modified, their hash value could change, making them unsuitable for use as keys.

To use a collection of elements as keys in a dictionary, you can use tuples instead. Tuples are immutable and therefore hashable, making them suitable for use as dictionary keys. Alternatively, you can convert the list into a tuple before using it as a key.

## Decorators and their example.
A decorator in Python is a design pattern that allows you to add functionality to an existing function or method without modifying its structure. It is implemented as a callable object (usually a function) that takes another function as an argument and returns a new function, typically with some modifications.

Here's a breakdown of how decorators work:

1. **Accepts a Function**: Decorators accept a function (or method) as their argument. This function is typically referred to as the "target" function, which you want to enhance or modify.

2. **Returns a Function**: Decorators return a new function, often called a "wrapper" function, which usually extends the behavior of the original function by adding some functionality before or after its execution, or by modifying its input or output.

3. **Functionality Extension**: Decorators allow you to add functionality such as logging, caching, input validation, authentication, or performance monitoring to functions, without directly modifying their source code.

4. **Syntactic Sugar**: Python provides a convenient syntactic sugar for applying decorators using the "@" symbol followed by the decorator name just above the function definition. This syntax simplifies the process of applying decorators to functions.

Overall, decorators provide a powerful way to enhance the behavior of functions in a flexible and reusable manner, promoting clean and modular code design.

```python
def repeat(num_times):
    def decorator_repeat(func):
        def wrapper(*args, **kwargs):
            for _ in range(num_times):
                result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator_repeat

@repeat(num_times=3)
def greet1(name):
    print(f"Hello, {name}!")

greet1("Alice")

def greet2(name):
    print(f"Hello, {name}!")

# Manually applying the decorator
greet2 = repeat(3)(greet2)

greet2("Bob")
```

## SQL Query to get the name of student having 2nd maximum marks.
### Using Nested Queries
```sql
SELECT name
FROM students
WHERE marks = (
    SELECT MAX(marks)
    FROM students
    WHERE marks < (
        SELECT MAX(marks)
        FROM students
    )
);
```

### Using LIMIT and OFFSET
```sql
SELECT name
FROM students
ORDER BY marks DESC
LIMIT 1 OFFSET 1;
```

### Using Common Table Expression (CTE) along with the ROW_NUMBER
```sql
WITH RankedStudents AS (
    SELECT name, marks, ROW_NUMBER() OVER (ORDER BY marks DESC) AS rank
    FROM students
)
SELECT name
FROM RankedStudents
WHERE rank = 2;
```

## List 10 uncommon linux commands.

1. **`tac`**: Reverse lines of a file. It prints each line of the file in reverse order.

2. **`fold`**: Wrap each input line to fit in the specified width. It breaks long lines into multiple lines to fit within the specified width.

3. **`comm`**: Compare two sorted files line by line. It displays lines that are common, unique to the first file, and unique to the second file.

4. **`pr`**: Convert text files for printing. It paginates or columnates files for printing, typically used in conjunction with printers.

5. **`rename`**: Rename multiple files according to a pattern. It renames files based on a specified pattern or substitution.

6. **`join`**: Join lines of two files on a common field. It merges two files based on a common field or key.

7. **`script`**: Make typescript of terminal session. It records everything displayed on the terminal into a file, capturing both input and output.

8. **`look`**: Display lines beginning with a given string. It searches for lines beginning with a specified string in a sorted file.

9. **`at`**: Schedule a one-time task to be executed at a specific time. It allows you to schedule commands or scripts to be executed once at a specified time.

10. **`timeout`**: Run a command with a time limit. It runs a command with a specified time limit and terminates it if it exceeds the specified duration.

## Find a file names.txt in /home
```bash
find /home -name names.txt
```

## File names.txt contains names in each line, write a bash program to print each name line by line.

### Using IFS
```bash
#!/bin/bash

# Check if names.txt exists
if [ ! -f "names.txt" ]; then
    echo "names.txt not found!"
    exit 1
fi

# Read names line by line and print
while IFS= read -r name; do
    echo "$name"
done < names.txt
```

### Using AWK
```bash
#!/bin/bash

# Check if names.txt exists
if [ ! -f "names.txt" ]; then
    echo "names.txt not found!"
    exit 1
fi

# Use awk to print each name line by line
awk '{print}' names.txt
```