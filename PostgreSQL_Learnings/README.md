# SQL and PostgreSQL

## Introduction
SQL - It is the Structured Query Language. It is a programming language.
- 1974
- Manage data held in a Relational Database.
- Data stored in Table, (Column, Row)

PostgreSQL - It is the Database Engine.
- Object-Relational Database Management System

> # PostgreSQL

## Installation

Visit https://www.postgresql.org/ and download your OS-specific version

## Running the Server

Start SQL Shell (psql) 

## Commands

```bash
\? : Quit
\help : Help
psql --help : Help
\l : List all the databases
\c dbname : to connect to a database
\d : List of Relations
\dt : List of Tables
\i SQL FILE LOCATION : Apply commands from .sql file
```

## Database

What is a Database?
- Store
- Manipulate
- Retrieve

### Creating test database

```sql
CREATE DATABASE test;
```

### Connecting to test database
```sql
~ psql -h localhost -p 5432 -U postgre test
~ \c dbname
```

### Deleting Database
```sql
~ DROP DATABASE test;
```

## Datatypes in PSQL

| **Name**                                    	| **Aliases**            	| **Description**                                                      	|
|-----------------------------------------	|--------------------	|------------------------------------------------------------------	|
| bigint                                  	| int8               	| signed eight-byte integer                                        	|
| bigserial                               	| serial8            	| autoincrementing eight-byte integer                              	|
| bit [ (n) ]                             	|                    	| fixed-length bit string                                          	|
| bit varying [ (n) ]                     	| varbit [ (n) ]     	| variable-length bit string                                       	|
| boolean                                 	| bool               	| logical Boolean (true/false)                                     	|
| box                                     	|                    	| rectangular box on a plane                                       	|
| bytea                                   	|                    	| binary data (“byte array”)                                       	|
| character [ (n) ]                       	| char [ (n) ]       	| fixed-length character string                                    	|
| character varying [ (n) ]               	| varchar [ (n) ]    	| variable-length character string                                 	|
| cidr                                    	|                    	| IPv4 or IPv6 network address                                     	|
| circle                                  	|                    	| circle on a plane                                                	|
| date                                    	|                    	| calendar date (year, month, day)                                 	|
| double precision                        	| float8             	| double precision floating-point number (8 bytes)                 	|
| inet                                    	|                    	| IPv4 or IPv6 host address                                        	|
| integer                                 	| int, int4          	| signed four-byte integer                                         	|
| interval [ fields ] [ (p) ]             	|                    	| time span                                                        	|
| json                                    	|                    	| textual JSON data                                                	|
| jsonb                                   	|                    	| binary JSON data, decomposed                                     	|
| line                                    	|                    	| infinite line on a plane                                         	|
| lseg                                    	|                    	| line segment on a plane                                          	|
| macaddr                                 	|                    	| MAC (Media Access Control) address                               	|
| macaddr8                                	|                    	| MAC (Media Access Control) address (EUI-64 format)               	|
| money                                   	|                    	| currency amount                                                  	|
| numeric [ (p, s) ]                      	| decimal [ (p, s) ] 	| exact numeric of selectable precision                            	|
| path                                    	|                    	| geometric path on a plane                                        	|
| pg_lsn                                  	|                    	| PostgreSQL Log Sequence Number                                   	|
| pg_snapshot                             	|                    	| user-level transaction ID snapshot                               	|
| point                                   	|                    	| geometric point on a plane                                       	|
| polygon                                 	|                    	| closed geometric path on a plane                                 	|
| real                                    	| float4             	| single precision floating-point number (4 bytes)                 	|
| smallint                                	| int2               	| signed two-byte integer                                          	|
| smallserial                             	| serial2            	| autoincrementing two-byte integer                                	|
| serial                                  	| serial4            	| autoincrementing four-byte integer                               	|
| text                                    	|                    	| variable-length character string                                 	|
| time [ (p) ] [ without time zone ]      	|                    	| time of day (no time zone)                                       	|
| time [ (p) ] with time zone             	| timetz             	| time of day, including time zone                                 	|
| timestamp [ (p) ] [ without time zone ] 	|                    	| date and time (no time zone)                                     	|
| timestamp [ (p) ] with time zone        	| timestamptz        	| date and time, including time zone                               	|
| tsquery                                 	|                    	| text search query                                                	|
| tsvector                                	|                    	| text search document                                             	|
| txid_snapshot                           	|                    	| user-level transaction ID snapshot (deprecated; see pg_snapshot) 	|
| uuid                                    	|                    	| universally unique identifier                                    	|
| xml                                     	|                    	| XML data                                                         	|

# Table

### Table Creation

<blockquote>
CREATE TABLE table_name {
  Column_name + Data_type + Constraint if any,
};
</blockquote>

<br/>

#### Creating a Table (without constraint)
```sql
test=# CREATE TABLE person(
  id INT,
  first_name VARCHAR(50),
  last_name VARCHAR(50),
  gender VARCHAR(7),
  date_of_birth DATE );
```

<img src=".\Images\Create_Table_without-constraint.png" alt="Terminal snapshot Table Creation without constraint" />

#### Creating a Table (with constraint)
```sql
test=# CREATE TABLE person(
  id BIGSERIAL NOT NULL PRIMARY KEY,
  first_name VARCHAR(50) NOT NULL,
  last_name VARCHAR(50) NOT NULL,
  gender VARCHAR(7) NOT NULL,
  date_of_birth DATE NOT NULL,
  email VARCHAR(150));
```

<img src=".\Images\Create_Table_with-constraint.png" alt="Terminal snapshot Table Creation with constraint" />
<img src=".\Images\Table_with_constraint.png" alt="Terminal snapshot Table Creation with constraint" />


## List Table of Connected Database

- \b: To describe the tables of connected database
- \b table_name: To know the details of the table_name

<img src=".\Images\Table_Info.png" alt="Terminal snapshot for Table Infor"/>

<br/>

## Delete Table
<blockquote>
DROP TABLE table_name;
</blockquote>

<br/>

<img src=".\Images\Drop_table.png" alt="Terminal snapshot for Delete Table"/>

<br/>

# Table Operations

## Insertions

<blockquote>
INSERT INTO table_name (
  Column_name_1,
  Column_name_2
) VALUES (
  Value_1,
  Value_2
);
</blockquote>

```sql
INSERT INTO person (first_name, last_name, gender, date_of_birth) VALUES ('Anne', 'Smith', 'FEMALE', date '1981-01-09');

INSERT INTO person (first_name, last_name, gender, date_of_birth, email) VALUES ('Jake', 'Jonas', 'MALE', date '1990-12-31', 'jake@gmail.com');
```
<img src=".\Images\Insert_command.png" alt="Terminal snapshot for Insert Command"/>


<blockquote>
For Values of type 'BIGSERIAL', you don't need to provide value, they are auto-incremented.

https://www.mockaroo.com/ to generate a random dataset
</blockquote>

## SELECT Command

<blockquote>
SELECT
"Column Names"/*
FROM table_name;
</blockquote>

```sql
SELECT * FROM person;
```

<img src=".\Images\Inserted_Content.png" alt="Terminal snapshot for the Inserted Content"/>

We can apply clauses to the output of the "SELECT" command.

### ORDER BY Clause

Order the output of the command based on columns
1. Ascending Order: In the increasing order
2. Descending Order: In the decreasing order

```sql
SELECT * FROM person ORDER BY country_of_birth ASC;
```
<img src=".\Images\Order_by_asc_clause.png"/>

```sql
SELECT * FROM person ORDER BY country_of_birth DESC;
```
<img src=".\Images\Order_by_desc_clause.png"/>

### DISTINCT Clause

To get rid of duplicate values.

```sql
SELECT DISTINCT country_of_birth FROM person;
```
<img src=".\Images\Distinct_clause.png"/>

### WHERE Clause
To apply conditions on the output of the "SELECT" command

```sql
SELECT * FROM person WHERE gender = "Female";
```
<img src=".\Images\Where_clause.png"/>

#### Using AND condition

```sql
SELECT * FROM person WHERE gender = 'Male' AND country_of_birth = 'Poland';
```
<img src=".\Images\Where_clause_and.png"/>

#### Using OR condition

```sql
SELECT * FROM person WHERE gender = 'Male' AND (country_of_birth = 'Poland' or country_of_birth = 'China');
```
<img src=".\Images\Where_clause_or.png"/>

#### Comparison Operators

These operators return True or False, based on the operands.

| Operator 	|        Known AS       	| Operand A 	| Operand B 	| Output 	|
|:--------:	|:---------------------:	|:---------:	|:---------:	|:------:	|
|     =    	|        Equal To       	|     5     	|     4     	|  False 	|
|     =    	|        Equal To       	|     5     	|     5     	|  True  	|
|     >    	|      Greater Than     	|     5     	|     5     	|  False 	|
|     >    	|      Greater Than     	|     5     	|     4     	|  True  	|
|     <    	|       Less Than       	|     5     	|     5     	|  False 	|
|     <    	|       Less Than       	|     4     	|     5     	|  True  	|
|    >=    	| Greater Than Equal To 	|     5     	|     6     	|  False 	|
|    >=    	| Greater Than Equal To 	|     5     	|     5     	|  True  	|
|    >=    	| Greater Than Equal To 	|     5     	|     4     	|  True  	|
|    <=    	|   Less Than Equal To  	|     5     	|     6     	|  True  	|
|    <=    	|   Less Than Equal To  	|     5     	|     5     	|  True  	|
|    <=    	|   Less Than Equal To  	|     5     	|     4     	|  False 	|
|    <>    	|      Not Equal To     	|     5     	|     5     	|  False 	|
|    <>    	|      Not Equal To     	|     5     	|     4     	|  True  	|


#### IN Operator
This operator helps to check the presence of operand A in a set/group.

```sql
SELECT * FROM person WHERE country_of_birth IN ('Brazil', 'China', 'France');
```
<img src=".\Images\IN_operator.png"/>

#### BETWEEN N AND M Operator
This operator helps to check the presence of operand A in a defined range.

```sql
SELECT * FROM person WHERE date_of_birth BETWEEN date '2000-01-01' AND '2001-01-01';
```
<img src=".\Images\BETWEEN_operator.png"/>

#### LIKE Operator

This operator helps to match operand A with Operand B.

- '%' Wildcard: This card will match anything and any number of times.
- '_' Wildcard: This card will match anything for one time.

```sql
SELECT * FROM person WHERE email LIKE '%@intel%';
```

<img src=".\Images\LIKE_wildcar_1_operator.png"/>

```sql
 SELECT * FROM person WHERE email LIKE 'a_s%';
```

<img src=".\Images\LIKE_wildcar_2_operator.png"/>

#### ILIKE Operator

Same as a Like operator but has no case-sensitive comparisons. 

```sql
SELECT * FROM person WHERE email ILIKE 'p%';
```

<img src=".\Images\ILIKE_wildcar_1_operator.png"/>

```sql
 SELECT * FROM person WHERE email ILIKE 'a_s%';
```

<img src=".\Images\ILIKE_wildcar_2_operator.png"/>

### GROUP BY Clause
This clause is used to group data, based on any column that is returned by the "SELECT" command.

```sql
SELECT country_of_birth, COUNT(*) FROM person GROUP BY country_of_birth;
```

<img src=".\Images\GROUP_BY_clause.png"/>

### GROUP BY X HAVING Y Clause
This clause is used to group data, based on any column that is returned by the "SELECT" command, X and then apply condition Y to the result

```sql
SELECT country_of_birth, COUNT(*) FROM person GROUP BY country_of_birth HAVING COUNT(*)>10;
```

<img src=".\Images\GROUP_BY_HAVING_clause.png"/>

#### Aggregate Functions

| Function                          	| Argument Type(s)                                                                	| Return Type                                                                                                                         	| Description                                                                                                                          	|
|-----------------------------------	|---------------------------------------------------------------------------------	|-------------------------------------------------------------------------------------------------------------------------------------	|--------------------------------------------------------------------------------------------------------------------------------------	|
| array_agg(expression)             	| any non-array type                                                              	| array of the argument type                                                                                                          	| input values, including nulls, concatenated into an array                                                                            	|
| array_agg(expression)             	| any array type                                                                  	| same as argument data type                                                                                                          	| input arrays concatenated into array of one higher dimension (inputs must all have same dimensionality, and cannot be empty or null) 	|
| avg(expression)                   	| smallint, int, bigint, real, double precision, numeric, or interval             	| numeric for any integer-type argument, double precision for a floating-point argument, otherwise the same as the argument data type 	| the average (arithmetic mean) of all non-null input values                                                                           	|
| bit_and(expression)               	| smallint, int, bigint, or bit                                                   	| same as argument data type                                                                                                          	| the bitwise AND of all non-null input values, or null if none                                                                        	|
| bit_or(expression)                	| smallint, int, bigint, or bit                                                   	| same as argument data type                                                                                                          	| the bitwise OR of all non-null input values, or null if none                                                                         	|
| bool_and(expression)              	| bool                                                                            	| bool                                                                                                                                	| true if all input values are true, otherwise false                                                                                   	|
| bool_or(expression)               	| bool                                                                            	| bool                                                                                                                                	| true if at least one input value is true, otherwise false                                                                            	|
| count(*)                          	|                                                                                 	| bigint                                                                                                                              	| number of input rows                                                                                                                 	|
| count(expression)                 	| any                                                                             	| bigint                                                                                                                              	| number of input rows for which the value of expression is not null                                                                   	|
| every(expression)                 	| bool                                                                            	| bool                                                                                                                                	| equivalent to bool_and                                                                                                               	|
| json_agg(expression)              	| any                                                                             	| json                                                                                                                                	| aggregates values, including nulls, as a JSON array                                                                                  	|
| jsonb_agg(expression)             	| any                                                                             	| jsonb                                                                                                                               	| aggregates values, including nulls, as a JSON array                                                                                  	|
| json_object_agg(name, value)      	| (any, any)                                                                      	| json                                                                                                                                	| aggregates name/value pairs as a JSON object; values can be null, but not names                                                      	|
| jsonb_object_agg(name, value)     	| (any, any)                                                                      	| jsonb                                                                                                                               	| aggregates name/value pairs as a JSON object; values can be null, but not names                                                      	|
| max(expression)                   	| any numeric, string, date/time, network, or enum type, or arrays of these types 	| same as argument type                                                                                                               	| maximum value of expression across all non-null input values                                                                         	|
| min(expression)                   	| any numeric, string, date/time, network, or enum type, or arrays of these types 	| same as argument type                                                                                                               	| minimum value of expression across all non-null input values                                                                         	|
| string_agg(expression, delimiter) 	| (text, text) or (bytea, bytea)                                                  	| same as argument types                                                                                                              	| non-null input values concatenated into a string, separated by delimiter                                                             	|
| sum(expression)                   	| smallint, int, bigint, real, double precision, numeric, interval, or money      	| bigint for smallint or int arguments, numeric for bigint arguments, otherwise the same as the argument data type                    	| sum of expression across all non-null input values                                                                                   	|
| xmlagg(expression)                	| xml                                                                             	| xml                                                                                                                                 	| concatenation of non-null XML values (see also Section 9.14.1.7                                                                      	|

### LIMIT N Keyword
This keyword helps to restrict/limit the number of rows for the output of the "SELECT" command. It will return only up to N rows, from TOP.


```sql
SELECT * FROM person LIMIT 10;
```
<img src=".\Images\Limit_keyword.png"/>

### OFFSET M Keyword
This Keyword helps to ignore the number of rows for the output of the "SELECT" command. It will return after the Mth rows from TOP.

```sql
SELECT * FROM person OFFSET 5;
```
<img src=".\Images\Offset_keyword.png"/>

### OFFSET M LIMIT N Keyword
This keyword helps to ignore the M number of rows for the output of the "SELECT" command and then return only TOP N rows.

```sql
SELECT * FROM person OFFSET 5 LIMIT 4;
OR
SELECT * FROM person LIMIT 4 OFFSET 5;
```
<img src=".\Images\Offset_limit_keyword.png"/>

### FETCH FIRST N ROWS ONLY Keyword
This keyword helps to restrict/limit the number of rows for the output of the "SELECT" command. It will return only up to N rows, from TOP.

```sql
SELECT * FROM person FETCH FIRST 5 ROWS ONLY;
```
<img src=".\Images\Fetch_first_N_rows_only_keyword.png"/>


### Calculating MIN, MAX and AVERAGE

#### MIN

```sql
SELECT MIN(price) FROM car;
```

<img src=".\Images\MIN.png"/>

#### MAX

```sql
SELECT MAX(price) FROM car;
```

<img src=".\Images\MAX.png"/>

#### AVG

```sql
SELECT AVG(price) FROM car;
```

<img src=".\Images\AVG.png"/>


## Arithmetics Operator

```sql
SELECT id, make, model, price, round(price-price*0.10,2) FROM car;
```

<img src=".\Images\Arithmetical_operation.png"/>

# Other Keywords and Functions

## ALIAS

```sql
SELECT id, make, model, price, round(price-price*0.10,2) AS discounted_price FROM car;
```

<img src=".\Images\Arithmetical_operation_with_alias.png"/>


## COALESCE
This Keyword/function is used when we want to replace null/empty values with something else;
<blockquote>
COALESCE(A, B, C, ...): This will return the first not null value.
</blockquote>

```sql
SELECT email FROM person;
```
<img src=".\Images\COALESCE_without.png"/>

```sql
SELECT COALESCE(email, 'No Email Found') FROM person;
```
<img src=".\Images\COALESCE_with.png"/>


## NULLIF
This keyword/function takes two values, if both values are equal it returns null else it returns the first value.
```sql
SELECT NULLIF(10,10);
SELECT NULLIF(10,5);
```

<img src=".\Images\NULLIF_use.png"/>

### Handling Divide By Zero using COALESCE and NULLIF

```sql
SELECT COALESCE(10/NULLIF(0,0),0);
```
<img src=".\Images\Divide_by_zero.png"/>

## TIMESTAMP and DATE

### NOW
```sql
SELECT NOW();
```

<img src=".\Images\NOW.png"/>

### NOW()::DATE
```sql
SELECT NOW()::DATE;
```

<img src=".\Images\NOW_DATE.png"/>


### NOW()::TIME
```sql
SELECT NOW()::TIME;
```

<img src=".\Images\NOW_TIME.png"/>

### INTERVAL
```sql
SELECT NOW(), NOW() - INTERVAL '10 YEARS';
SELECT NOW(), NOW() - INTERVAL '10 YEAR';
```

<img src=".\Images\INTERVAL.png"/>

```sql
SELECT NOW(), NOW() - INTERVAL '10 MONTHS';
SELECT NOW(), NOW() - INTERVAL '10 DAY';
SELECT NOW(), NOW() + INTERVAL '10 DAY';
SELECT NOW(), NOW() + INTERVAL '10 DAYS';
```

<img src=".\Images\INTERVAL_1.png"/>

```sql
SELECT NOW(), NOW() + INTERVAL '10 HOURS';
SELECT NOW(), NOW() + INTERVAL '10 MINUTES';
SELECT NOW(), NOW() + INTERVAL '10 SECONDS';
```
<img src=".\Images\INTERVAL_2.png"/>

### EXTRACT

```sql
SELECT NOW(), EXTRACT(YEAR FROM NOW()), EXTRACT(MONTH FROM NOW()), EXTRACT(DAY FROM NOW()), EXTRACT(HOURS FROM NOW()), EXTRACT(MINUTES FROM NOW()), EXTRACT(SECONDS FROM NOW());
```

<img src=".\Images\EXTRACT.png"/>

# CONSTRAINTS

## PRIMARY KEYS CONSTRAINT
It is a value/column that uniquely defines each row, and it can be used to distinguish each row.


To remove a PRIMARY KEY constraint
```sql
\d person
ALTER TABLE person DROP CONSTRAINT person_pkey;
\d person
```
<img src=".\Images\DROP_CONSTRAINT_primary_key.png"/>

To add a PRIMARY KEY constraint
```sql
\d person
ALTER TABLE person ADD CONSTRAINT person_pkey PRIMARY KEY (id);
\d person
```

<img src=".\Images\ADD_CONSTRAINT_primary_key.png"/>

## UNIQUE CONSTRAINT

To add a UNIQUE constraint
```sql
\d person
ALTER TABLE person ADD CONSTRAINT unique_email_address UNIQUE(email);
\d person
```
<img src=".\Images\ADD_CONSTRAINT_unique.png"/>

To remove a UNIQUE constraint
```sql
\d person
ALTER TABLE person DROP CONSTRAINT unique_email_address;
\d person
```
<img src=".\Images\DROP_CONSTRAINT_unique.png"/>

## CHECK CONSTRAINT

To add a UNIQUE constraint
```sql
\d person
ALTER TABLE person ADD CONSTRAINT gender_constraint CHECK (gender IN ('Genderqueer', 'Bigender', 'Genderfluid', 'Male', 'Polygender', 'Non-binary', 'Female', 'Agender'));
\d person
```
<img src=".\Images\ADD_CONSTRAINT_check.png"/>

To remove a UNIQUE constraint
```sql
\d person
ALTER TABLE person DROP CONSTRAINT gender_constraint;
\d person
```
<img src=".\Images\DROP_CONSTRAINT_check.png"/>