> # Data Preprocessing

## Importing the Libraries
- numpy
: To work with arrays

- matplotlib
: To plot graphs

- pandas
: To work with data matrices and vectors

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
```

## Importing the Dataset
| Country | Age  | Salary  | Purchased |
|---------|------|---------|-----------|
| France  | 44.0 | 72000.0 | No        |
| Spain   | 27.0 | 48000.0 | Yes       |
| Germany | 30.0 | 54000.0 | No        |
| Spain   | 38.0 | 61000.0 | No        |
| Germany | 40.0 | NaN     | Yes       |
| France  | 35.0 | 58000.0 | Yes       |
| Spain   | NaN  | 52000.0 | No        |
| France  | 48.0 | 79000.0 | Yes       |
| Germany | 50.0 | 83000.0 | No        |
| France  | 37.0 | 67000.0 | Yes       |
```python
dataset = pd.read_csv('../Path/Data.csv')
X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values
print(X)
print(y)
```

## Taking care of missing data
1. Exclude rows of missing Data
2. Replacing missing values to
    - Mean value
    - Median value
    - Mode value


## Importing other modules

- scikit-learn
: module for machine learning and data mining


```python
from sklearn.impute import SimpleImputer
imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
imputer.fit(X[:,1:3])
X[:,1:3] = imputer.transform(X[:,1:3])
print(X)
```

| Country | Age  | Salary  | Purchased |
|---------|------|---------|-----------|
| France  | 44.0 | 72000.0 | No        |
| Spain   | 27.0 | 48000.0 | Yes       |
| Germany | 30.0 | 54000.0 | No        |
| Spain   | 38.0 | 61000.0 | No        |
| Germany | 40.0 | 63777.7 | Yes       |
| France  | 35.0 | 58000.0 | Yes       |
| Spain   | 38.8 | 52000.0 | No        |
| France  | 48.0 | 79000.0 | Yes       |
| Germany | 50.0 | 83000.0 | No        |
| France  | 37.0 | 67000.0 | Yes       |

## Encoding categorial data [Independent Variable]
Categorial data, needs to be encoded to numerical data type
- OneHotEncoder
: converts a categorial data column into sevral columns of 0 and 1


```python
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[0])], remainder='passthrough')
X = np.array(ct.fit_transform(X))
print(X)
```


| Country0 | Country1 | Country1 | Age  | Salary   | Purchased |
|----------|----------|----------|------|----------|-----------|
| 1.0      | 0.0      | 0.0      | 44.0 | 72000.0  | No        |
| 0.0      | 0.0      | 1.0      | 27.0 | 48000.0  | Yes       |
| 0.0      | 1.0      | 0.0      | 30.0 | 54000.0  | No        |
| 0.0      | 0.0      | 1.0      | 38.0 | 61000.0  | No        |
| 0.0      | 1.0      | 0.0      | 40.0 | 63777.8  | Yes       |
| 1.0      | 0.0      | 0.0      | 35.0 | 58000.0  | Yes       |
| 0.0      | 0.0      | 1.0      | 38.8 | 52000.0  | No        |
| 1.0      | 0.0      | 0.0      | 48.0 | 79000.0  | Yes       |
| 0.0      | 1.0      | 0.0      | 50.0 | 83000.0  | No        |
| 1.0      | 0.0      | 0.0      | 37.0 | 67000.0  | Yes       |

## Encoding categorial data [Dependent Variable]
- Label Encoder
: Convert categorial data into binary

```python
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
y = le.fit_transform(y)
print(y)
```

| Country0 | Country1 | Country2 | Age  | Salary   | Purchased |
|----------|----------|----------|------|----------|-----------|
| 1.0      | 0.0      | 0.0      | 44.0 | 72000.0  | 0         |
| 0.0      | 0.0      | 1.0      | 27.0 | 48000.0  | 1         |
| 0.0      | 1.0      | 0.0      | 30.0 | 54000.0  | 0         |
| 0.0      | 0.0      | 1.0      | 38.0 | 61000.0  | 0         |
| 0.0      | 1.0      | 0.0      | 40.0 | 63777.8  | 1         |
| 1.0      | 0.0      | 0.0      | 35.0 | 58000.0] | 1         |
| 0.0      | 0.0      | 1.0      | 38.8 | 52000.0  | 0         |
| 1.0      | 0.0      | 0.0      | 48.0 | 79000.0  | 1         |
| 0.0      | 1.0      | 0.0      | 50.0 | 83000.0  | 0         |
| 1.0      | 0.0      | 0.0      | 37.0 | 67000.0  | 1         |

## Spliting the dataset into Training and Test data
Split dataset into train and test data, to test the model

```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

## Feature Scaling
Scaling Dataset, such that all the values lie inside a small range
- Standardisation
: This will scale values to [-3,+3]

$$ X_{stand} = \frac{x- X_{mean}}{standard \ \ deviation(X)} $$

- Normalisation
: This will scale values to [0,1]

$$ X_{norm} = \frac{x- X_{mean}}{max(X)-min(X)} $$

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train[:,3:])
# transform training data using the scaler
X_train[:,3:] = sc.transform(X_train[:,3:])
# transform test data using the same scaler
X_test[:,3:] = sc.transform(X_test[:,3:])
```

<br/>
<hr/>
<br/>

> # Regression

## Simple Linear Regression

### Predicts continious numerical values
In simple linear regression, we simply predict value based on an equation

$$ y = b_{0} \ \ + \ \ b_{1}x $$

In above equation, y will depend on the values of x, so we can predict/calculate value of y, if value of x is already known.


### Loading the Dataset

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd 

dataset = pd.read_csv("./Regression/Simple_Linear_Regression/Datasets/Salary_Data.csv")

X=dataset.iloc[:,:-1].values
y=dataset.iloc[:,-1].values


from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Training the Simple Regression Model on the Training dataset

In this step, Simple Linear Regression model is trained using the training dataset.   
Simply equation for the Linear Regression is computed, using training dataset.

```python
from sklearn.linear_model import LinearRegression
regressor = LinearRegression()
regressor.fit(X_train, y_train)
```

### Predicting the result for Test Dataset
In this step, result for test data is predicted using above trained model.

```python
y_pred = regressor.predict(X_test)
print(y_pred)
print(y_test)
```

### Visualising the Training set result

```python
plt.scatter(X_train, y_train, color='red')
plt.plot(X_train, regressor.predict(X_train), color='blue')
plt.title('Experience vs Salary')
plt.xlabel('Years of Experience')
plt.ylable('Salary')
plt.show()
```

### Visualising the Test set result

```python
plt.scatter(X_test, y_test, color='red')
plt.plot(X_test, y_pred, color='blue')
plt.title('Experience vs Salary')
plt.xlabel('Years of Experience')
plt.ylable('Salary')
plt.show()
```

### Predict salary for a single Experience

```python
print(regressor.predict([[0]]))
```

### Computing the Linear Regression Equation

```python
n=len(X_train[0])
ans=[]
b0=regressor.predict([[0  for _ in range(n)]])
eq="y = "+str(b0[0])
for i in range(n):
    ar=[[0 for _ in range(i)]+[1]+[0 for _ in range(i+1,n)]]
    b=regressor.predict(ar)
    eq+=" + {}*x{}".format(b[0],i+1)
print(eq)
```

## Multiple Linear Regression

If there are multiple variables inside Linear Regression Equation, it is known as Multiple Linear Regression

Let's see equation

$$y = b_{0} \ \ + \ \ b_{1}x_{1}  \ \ + \ \ b_{2}x_{2}  \ \ + \ \ b_{3}x_{3} \ \ + \ \ ... \ \ + \ \ b_{n}x_{n}$$

Now y will depend on multiple values, we can still predict/calculate value of y, if we have the equation and the values of the X.

### Assumptions of Linear Regression
There are 5 assumptions
1. Linearity
2. Homoscedasticity
3. Multivariate Normality
4. Independence of Errors
5. Lack of Multicollinearity

### Hypothesis Testing (P-Value)
Supose you have a coin, and you are tossing it continiously
1. got HEAD, its probability is 0.5
2. got again HEAD, its probability is 0.25
3. got again HEAD, its probability is 0.12
4. got again HEAD, its probability is 0.06

If you get get HEAD again (probability 0.03), coin is suspicous. you may think coin is not a fair coin.
The point/percent at which you become suspicious is known as **Significance Value**.

Initially we assume coin is fair, but when the significance value is reached, we correct our assumption (Hypothesis) and confirm that it is not a fair coin, this is known as **Null Hypothesis Testing**.

### Building a Multiple Linear Regression Model
There are 5 ways to build Multiple Linear Regression Model
1. All In
:  Select all the columns
    - You have prior knowledge
    - You have to select all columns
    - You are preparing for backward elimination
2. Backward Elimination (Fastest)
    1. Select a Significance Level to stay in the model (SL=0.05)
    2. Fit the model with all columns/predictor
    3. Select the column/predictor with highest P-Value, if P-Value > SL goto step 4, else go to FINISH
    4. Remove the predictor
    5. Fit the model again, and go to step 3
3. Forward Selection
    1. Select a Significance Level to Enter in the model (SL=0.05)
    2. Fit the model with all predictors seperately
    3. Select the predictor with lowest P-value, if P-value < SL goto step 4, else FINISH and keep the last model
    4. Fit the model, using all the remaining predictors separately and with this one extra combination
4. Bidirection Elemination
    1. Select a Significance Level to stay in the model (STAY_SL=0.05) and a Significance Level to Enter in the model (ENTER_SL=0.05)
    2. Perform next step of Forward Selection
    3. Perform all step of Backward Elimination
    4. When no new predictors enter and no old predictors can exit, FINISH
5. Score Comparision
    1. Select a criterion of goodness (Score)
    2. Construct all possible regression model (2<sup>N</sup>-1)
    3. Select the best model using goodness criterion
    4. FINISH

Step-wise Regression
- Backward Elimination
- Forward Selection
- Bidirection Elemination

### Loading Data and preprocessing it

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('./Datasets/Regression/Multiple_Linear_Regression/50_Startups.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

# Taking care of Missing values
from sklearn.impute import SimpleImputer 
imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
imputer.fit(X[:,:-1])
X[:,:-1] =  imputer.transform(X[:,:-1])
imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
imputer.fit(X[:,-2:-1])
X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
X = np.array(ct.fit_transform(X))
# print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Training the Linear Regression Model on the training set

```python
from sklearn.linear_model import LinearRegression
regressor = LinearRegression()
regressor.fit(X_train, y_train)
```

### Predicting the result for test set result

```python
y_pred = regressor.predict(X_test)
```

### Visualising the predicted and actual results

```python
np.set_printoptions(precision=2)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Computing the equation of model
```python
n = len(X_train[0])
b0=regressor.predict([[0 for _ in range(n)]])
eq="y = {}".format(b0[0])
for i in range(n):
    eq+=" + {}*x{}".format(regressor.predict([[0 for _ in range(i)]+[1]+[0 for _ in range(i+1,n)]])[0],i+1)
print(eq)
```

## Polynomial Regression

If the power raise to variable is not only 1, but may have different powers of the variable x, it is known as Polynomial Regression.
Let's see the equation

$$y = b_{0} \ \ + \ \ b_{1}x^{1}  \ \ + \ \ b_{2}x^{2}  \ \ + \ \ b_{3}x^{3} \ \ + \ \ ... \ \ + \ \ b_{n}x^{n}$$

Now y will depend on multiple powers of the x, we can still predict/calculate value of y, if we have the equation and the value of the x.

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Regression/Polynomial_Regression/Position_Salaries.csv')
# print(dataset)

X = dataset.iloc[:,1:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)

# Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# # Splitting dataset into train and test set
# from sklearn.model_selection import train_test_split
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Training the linear regression model on whole dataset

```python
from sklearn.linear_model import LinearRegression
lin_reg_1 =  LinearRegression()
lin_reg_1.fit(X,y)
```

### Training the polynomial regression model on whole dataset [ n=2 ]

```python
from sklearn.preprocessing  import PolynomialFeatures
poly_fet = PolynomialFeatures(degree=2)
poly_X = poly_fet.fit_transform(X)
lin_reg_2 = LinearRegression()
lin_reg_2.fit(poly_X,y)
```

### Visualising the Linear Regression result

```python
plt.scatter(X,y,color='red')
plt.plot(X,lin_reg_1.predict(X),color='blue')
plt.title('Truth or Bluff (Linear Regression Model)')
plt.show()
```

### Visualising the Polynomial Regression result

```python
plt.scatter(X,y,color='red')
plt.plot(X,lin_reg_2.predict(poly_X),color='blue')
plt.title('Truth or Bluff (Polynomial Regression Model) n=2')
plt.show()
```

### Training the polynomial regression model on whole dataset [ n=4 ]

```python
from sklearn.preprocessing  import PolynomialFeatures
poly_fet = PolynomialFeatures(degree=4)
poly_X = poly_fet.fit_transform(X)
lin_reg_2 = LinearRegression()
lin_reg_2.fit(poly_X,y)
```

### Visualising the Polynomial Regression result

```python
plt.scatter(X,y,color='red')
plt.plot(X,lin_reg_2.predict(poly_X),color='blue')
plt.title('Truth or Bluff (Polynomial Regression Model) n=4')
plt.show()
```

### Visualising the Polynomial Regression result with higher resolution and smoother curve

```python
from sklearn.preprocessing  import PolynomialFeatures

poly_fet = PolynomialFeatures(degree=4)
poly_X = poly_fet.fit_transform(X)
lin_reg_2 = LinearRegression()
lin_reg_2.fit(poly_X,y)
X_grid = np.arange(min(X),max(X),0.1)
X_grid = X_grid.reshape((len(X_grid),1))
plt.scatter(X,y,color='red')
plt.plot(X_grid,lin_reg_2.predict(poly_fet.fit_transform(X_grid)),color='blue')
plt.title('Truth or Bluff (Polynomial Regression Model) n=4, smooth curve')
plt.show()
```

### Predicting a new result using Linear Model

```python
lin_reg_1.predict([[6.5]])
```

### Predicting a new result using Polynomial Model

```python
lin_reg_2.predict(poly_fet.fit_transform([[6.5]]))
```

## Support Vector Regression [ SVR ]

In this regression, instead of a regression line, a hyperplane is used.\
Points lying insdie/on the hyperplane are allowed errors, Points lying outside the hyperplane are known as support vector,\
Hence this is known as **Support Vector Regression [SVR]**

### Loading Data and preprocessing it

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Regression/Support_Vector_Regression/Position_Salaries.csv')
# print(dataset)

X = dataset.iloc[:,1:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)

# Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# # Splitting dataset into train and test set
# from sklearn.model_selection import train_test_split
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler

sc_X = StandardScaler()
sc_X.fit(X)
X = sc_X.transform(X)

# reshape y
y = y.reshape((len(y),1))

sc_y = StandardScaler()
sc_y.fit(y)
y = sc_y.transform(y)

print(X)
print(y)
```

### Training the SVR model on the whole dataset

```python
from sklearn.svm import SVR
regressor =  SVR(kernel='rbf')
regressor.fit(X,y.ravel())
```

### Predict the salary for new test case

```python
y_pred = regressor.predict(sc_X.transform([[6.5]]))
print(y_pred)
y_pred = sc_y.inverse_transform(y_pred.reshape(1,1))
print(y_pred)
```

### Visualising the SVR model

```python
plt.scatter(sc_X.inverse_transform(X),sc_y.inverse_transform(y),color='red')
plt.plot(sc_X.inverse_transform(X),sc_y.inverse_transform(regressor.predict(X).reshape(len(y),1)),color='blue')
plt.title('Truth or Bluff (Support Vector Regression Model)')
plt.show()
```

### Visualising the SVR model in High Resolution

```python
X_grid = np.arange(min(sc_X.inverse_transform(X)),max(sc_X.inverse_transform(X)),0.1)
X_grid = X_grid.reshape((len(X_grid),1))
plt.scatter(sc_X.inverse_transform(X),sc_y.inverse_transform(y),color='red')
plt.plot(X_grid,sc_y.inverse_transform(regressor.predict(sc_X.transform(X_grid)).reshape(len(X_grid),1)),color='blue')
plt.title('Truth or Bluff (Support Vector Regression Model) smooth curve')
plt.show()
```

## Decision Tree Regression

In this we add some check [like if else] and based on the condition we predict the value 


**predict value of z, when values of x and y are given**

```python
if x < 20:
    if y < 200:
        z = 300.5
    else:
        z = 65.7
else:
    if y < 170:
        if x < 40:
            z = -64.1
        else:
            z = 0.7
    else:
        z = 1023
```

Basically we split our Dataset graph in various section, and for every new point we find the section in which new data lies, and then for prediction we just take average of that section.

### Load and preprocess the data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Regression/Decision_Tree_Regression/Position_Salaries.csv')
# print(dataset)

X = dataset.iloc[:,1:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)

# Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# # Splitting dataset into train and test set
# from sklearn.model_selection import train_test_split
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Training the Decision Tree Regression model on the whole dataset

```python
from sklearn.tree import DecisionTreeRegressor
regressor = DecisionTreeRegressor(random_state=0)
regressor.fit(X,y)
```

### Predicting the value for new test using Decision Tree Regressor

```python
regressor.predict([[6.5]])
```

### Visualising the Decision Tree Regression model [High Resolution]

```python
X_grid = np.arange(min(X),max(X),0.1)
X_grid = X_grid.reshape((len(X_grid),1))
plt.scatter(X,y,color='red')
plt.plot(X_grid,regressor.predict(X_grid),color='blue')
plt.title('Truth or Bluff (Decision Tree Regression Model) smooth curve')
plt.show()
```

## Random Forest Regression [Ensemble Learning]

### Steps/Procedure

1. Pick a number K, and select K random Data Points from the dataset
2. Build a Decision Tree associated with these K points
3. Pick a random[large] number N and build N Decision Tree using Step 1 and Step 2.
4. To predict for a test, First predict using all the N Decision Trees as y<sub>1</sub>, y<sub>2</sub>, y<sub>3</sub>, ... , y<sub>N</sub>.
5. Now take the average of the N values

### Load and preprocess Dataset

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Regression/Random_Forest_Regression/Position_Salaries.csv')
# print(dataset)

X = dataset.iloc[:,1:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)

# Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# # Splitting dataset into train and test set
# from sklearn.model_selection import train_test_split
# X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

### Train the Random Forest Regression Model using whole dataset

```python
from sklearn.ensemble import RandomForestRegressor
regressor = RandomForestRegressor(n_estimators=10, random_state=0)
regressor.fit(X,y)
```

### Predict the result for a new test

```python
regressor.predict([[6.5]])
```

### Visualisation of the Random Forest Regression Model

```python
plt.scatter(X,y,color='red')
plt.plot(X,regressor.predict(X),color='blue')
plt.title('Truth or Bluff (Random Forest Regression Model) smooth curve')
plt.show()
```

### Visualisation of the Random Forest Regression Model [High Resolution]

```python
X_grid = np.arange(min(X),max(X),0.1)
X_grid = X_grid.reshape((len(X_grid),1))
plt.scatter(X,y,color='red')
plt.plot(X_grid,regressor.predict(X_grid),color='blue')
plt.title('Truth or Bluff (Random Forest Regression Model) smooth curve')
plt.show()
```

## R-Square method to comare the models

Suppose the points on the regression line are

$$ Y = mx + C $$

$$ RY_{1}, \  RY_{2}, \  RY_{3}, \  ... \  , \  RY_{n} $$

Now lets Assume Y<sub>Avg</sub> is average of all given y points, and the equation for average prediction regression is

$$ Y = Y_{Avg} $$

### Squared Sum of Residuals 
$$ SS_{res} = \sum_{i=1}^{n} (Y_{i}-RY_{i})^2 $$

### Squared Sum Total
$$ SS_{tot} = \sum_{i=1}^{n} (Y_{i}-Y_{Avg})^2 $$

### R-Square
$$ R^2 = 1 - \frac{SS_{res}}{SS_{tot}} $$

**If value of  R<sup>2</sup> is nearer to 1, model is good.**

### Adjusted R<sup>2</sup>

It is observed that, whenever you add a new independent variable in regression equation, SS<sub>res</sub> is either going to increase or be the same, So R<sup>2</sup> will always increase, hence this method will not help in case of adding a new variable in regression.
Now, 

$$ R^2_{adj} = 1 - (1-R^2) \frac{n-1}{n-p-1} $$

n - Sample Size

p - No of Independent variable used in regression

<br/>
<hr/>
<br/>

> # Regression Model Selection [ Comparing and finding best regresssion Model]

## Load and preprocess Dataset

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Regression/Model_Selection_Regression/Data.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)

# Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# print(X)

# Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=1)
```

## Prediction using Multiple Linear Regression

```python
from sklearn.linear_model import LinearRegression
regressor = LinearRegression()
regressor.fit(X_train, y_train)
y_pred_MLR = regressor.predict(X_test)
print(y_pred_MLR)
```

## Prediction using Polynomial Regression

```python
from sklearn.preprocessing  import PolynomialFeatures
from sklearn.linear_model import LinearRegression
poly_fet = PolynomialFeatures(degree=4)
poly_X = poly_fet.fit_transform(X_train)
poly_reg =  LinearRegression()
poly_reg.fit(poly_X,y_train)
y_pred_PR = poly_reg.predict(poly_fet.fit_transform(X_test))
print(y_pred_PR)
```

## Prediction using Support Vector Regression

```python
from sklearn.preprocessing import StandardScaler

sc_X = StandardScaler()
sc_X.fit(X_train)
X_sc = sc_X.transform(X_train)

# reshape y
y_sc = y_train.reshape((len(y_train),1))

sc_y = StandardScaler()
sc_y.fit(y_sc)
y_sc = sc_y.transform(y_sc)

# print(X_sc)
# print(y_sc)

from sklearn.svm import SVR
regressor =  SVR(kernel='rbf')
regressor.fit(X_sc,y_sc.ravel())

y_pred_SVR = regressor.predict(sc_X.transform(X_test))
print(y_pred_SVR)
y_pred_SVR = sc_y.inverse_transform(y_pred_SVR.reshape(len(y_pred_SVR),1)).ravel()
print(y_pred_SVR)
```

## Prediction using Decision Tree Regression

```python
from sklearn.tree import DecisionTreeRegressor
regressor = DecisionTreeRegressor(random_state=0)
regressor.fit(X_train,y_train)
y_pred_DTR = regressor.predict(X_test)
print(y_pred_DTR)
```

## Prediction using Random Forest Regression

```python
from sklearn.ensemble import RandomForestRegressor
regressor = RandomForestRegressor(n_estimators=10, random_state=0)
regressor.fit(X_train,y_train)
y_pred_RFR = regressor.predict(X_test)
print(y_pred_RFR)
```

## R-Square Comparision for All model
```python
from sklearn.metrics import r2_score
R2S = {}
R2S['Multiple Linear Regression'] = r2_score(y_test, y_pred_MLR)
R2S['Polynomial Regression'] = r2_score(y_test, y_pred_PR)
R2S['Support Vector Regression'] = r2_score(y_test, y_pred_SVR)
R2S['Decision Tree Regression'] = r2_score(y_test, y_pred_DTR)
R2S['Random Forest Regression'] = r2_score(y_test, y_pred_RFR)

for method in R2S:
    print(method,":",R2S[method])
```

<br/>
<hr/>
<br/>

> # Classification

## Logistic Regression

Instead of predicting a value, when we try to pridict probability of any event, We use Logistic regression. The outcome of this forecast lies between 0 and 1

$$ y = b_{0} + b_{1}x $$

If we pass above linear eqaution to below Sigmoid function

$$ p = \frac{1}{1 + e^{-y}} $$

The generated eqation by comparing y on both equation comes out

$$ \ln{(\frac{p}{1 - p})} =  b_{0} + b_{1}x  $$

This above eqation is used in **Logistic Regression**.

Now we select a threshold value [0,1], if predicted probability is less than the threshhold value, Outcome is NO else YES.

### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Logistic_Regression/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```

### Training the Logistic Regression Model using Training Data

```python
from sklearn.linear_model import LogisticRegression
classifier = LogisticRegression(random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 0.25),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 0.25))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Logistic Regression (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 0.25),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 0.25))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Logistic Regression (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

## K-Nearest Neighbour

In this type of classification technique, we first select a value for K and then follow the below steps

1. Select the value of K. Generally the value of K is choosen is 5.
2. Select K Nearest Neighbour of the new Data Point. Usually Eucledian Distance is used to select Nearest Neighbours.
$$ D_{Eucledian\ Distance} = \sqrt{(x_{2}-x_{1})^{2}+(y_{2}-y_{1})^{2}}$$
3. Among these K Neighbours, count the number of datapoints in each category.
4. Assign the new data point to the category with most counted nearest neighbour.
5. Model is ready.


### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/K_Nearest_Neighbour/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```

### Training the K Nearest Neighbour Model using Training Data

```python
from sklearn.neighbors import KNeighborsClassifier
classifier = KNeighborsClassifier(n_neighbors = 5, metric = "minkowski", p = 2)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('K Nearest Neighbour (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('K Nearest Neighbour (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

## Support Vector Classification

Support Vector Classification is a little bit different type of classification. It draws a **Hyper-Line/Hyper-Plane** between different categories, but instead of finding the best line differentiating between categories, it finds the point/dataset which is worst point and then draw a **Hyper-Line/Hyper-Plane** having maximum margin.


Suppose we have one basket full of apples and one basket full of oranges. Now SVC will find an apple that is very much simillar to oranges, and an orange that is very much simillar to apple. Now SVC will find a **Hyper-Line/Hyper-Plane** that is giving highest margin between these points and use it to predict new datapoints.

### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Support_Vector_Classification/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the SVC Model using Training Data

```python
from sklearn.svm import SVC
classifier = SVC(kernel = 'linear', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('SVC (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('SVC (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

## Kernerl SVM

In Data Science, we are mainly dealing with Datasets. Now Datasets can be divided into two categories

- **Linearly Separable Data points**
: These data points can be easily seperated in different class/category using any hyperplane
- **Non Linearly Separable Data points**
: These data points can't be seperated in different class/category using any hyperplane

**Support Vector Machine [ SVM ]** can easily process datasets having **linearly separable datapoints** to predict classes/categories for new data points, but for **non linearly separable** data points SVM can't draw any hyperplane.

There is a technique **Maping to a Higher Dimension** which can be used to draw a hyperplane between non linearly seperable data points. In this technique, dimension of datapoints is increased to a higher dimension by using some equations/transformation.
Suppose we have two classes 1D datapoints
- Class A : [2, 3, 4, 8, 9, 10]
- Class B : [6, 7]

If we apply below transformation and increase dimenstion from 1D -> 2D
<br/>
y = f(x)
<br/>
y = (x-5)<sup>2</sup>

Now the resultant datapoints will be a hyperbola, and we can draw a line that will separate the Class A and Class B.

Next, we can reproject our new datapoints in older dimension.

But, **Maping to a High Dimension can be a highly compute-intensive**



### The Kernel Trick

The Gaussian RBF Kernel

$$ K\left ( \vec{x}, \vec{l^{i}} \right ) = e^{- \left ( \frac{\left \| \vec{x} -\vec{l^{i}} \right \|}{ 2\sigma ^{2}} \right )} $$

$$ \vec{x} = Data \ Points $$

$$ \vec{l^{i}} = Land \  Vector $$

$$ \sigma = Radius \ of \ the \ Circle $$

For every data points we have K<sub>1</sub>, K<sub>2</sub> , K<sub>3</sub> , K<sub>4</sub> , ... K<sub>n</sub>

Based of the value of K<sub>i</sub>, we can decide class/category of any datapoint, without doing any high dimension computing.

We also can have different combination of these K

$$ K_{1}\left ( \vec{x}, \vec{l^{1}} \right ) + K_{2}\left ( \vec{x}, \vec{l^{2}} \right )  $$

The above equation can predict for the **<span>&#8734;</span>** shape of data points 

### Types of Kernel Function

1. The Gaussian RBF Kernel

$$ K\left ( \vec{x}, \vec{l^{i}} \right ) = e^{- \left ( \frac{\left \| \vec{x} -\vec{l^{i}} \right \|}{ 2\sigma ^{2}} \right )} $$


2. The Sigmoid Kernel

$$ K(X, Y) = \tanh (\gamma \cdot X^{T}Y + r) $$

3. The Polynomial Kernel

$$ K(X, Y) = (\gamma \cdot X^{T}Y + r)^{d}, \ \gamma > 0 $$


<img src="./Classification/Kernel_SVM/Kernel_functions.pdf.png"/>


### Non Linear Kernel SVR

<img src="./Classification/Kernel_SVM/Non_Linear_SVR.png"/>



### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Kernel_SVM/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Kernel SVM Model using Training Data

```python
from sklearn.svm import SVC
classifier = SVC(kernel = 'rbf', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```


## Naive Bayes


### Bayes Theorem

Let E1, E2,…, En be a set of events associated with a sample space S, where all the events E1, E2,…, En have nonzero probability of occurrence and they form a partition of S. Let A be any event associated with S, then according to Bayes theorem,

$$ P(E_{i}\mid A) = \frac{P(E_{i}) \cdot P(A\mid E_{i})}{\sum_{k=1}^{n} P(E_{k}) \cdot P(A\mid E_{k}) } $$ 

for any k = 1, 2, 3, … , n

**Proof**

<pre>Probability of A given that B has occured</pre>
$$ P(A \mid B) = \frac{P(A \cap B)}{P(B)}  \  \  \  \  \  \  \  \  \  \ ...\  (1)$$
<pre>Probability of A given that B has occured</pre>
$$ P(B \mid A) = \frac{P(A \cap B)}{P(A)}  \  \  \  \  \  \  \  \  \  \ ...\  (2)$$

Now using (1) and (2)

$$ P(A \mid B) \cdot P(B) = P(A \cap B) = P(B \mid A) \cdot P(A) $$

$$ P(A \mid B) \cdot P(B) = P(B \mid A) \cdot P(A) $$

$$ P(A \mid B) = \frac{P(B \mid A) \cdot P(A)}{P(B)} $$


Example, 


Let's have two machines M<sub>1</sub> and M<sub>2</sub>, that builds Bolts. 

M<sub>1</sub> can built 30 Bolts and M<sub>2</sub> can build 20 Bolts per second respectively. 1% of the total bolts are defective, Also it was given that the chance of building defective bolts for each machine is 50%.

Now,
                    
$$ P(M_{1})  =\  \frac{30}{20+30} =\  \frac{30}{50} =\  0.6 $$

$$ P(M_{2})  =\  \frac{20}{20+30} =\  \frac{20}{50} =\  0.4 $$

$$ P(Defected)  =\  0.01 $$

$$ P(M_{1} \mid Defected)  =\  0.5 $$

$$ P(M_{2} \mid Defected)  =\  0.5 $$

<pre>P(Event A | Event B) means probability of Event A, if Event B is given </pre>

Now, Given a bolt build by M<sub>1</sub>, what is the probability it is defected?

Using Bayes Theorem

$$ P(Defected \mid M_{1}) = \frac{P(M_{1} \mid Defected) \cdot P(Defected)}{P(M_{1} \mid Defected)+P(M_{1} \mid Not\ Defected)} $$


$$ P(Defected \mid M_{1}) = \frac{P(M_{1} \mid Defected) \cdot P(Defected)}{P(M_{1})} $$


$$ P(Defected \mid M_{1}) = \frac{0.01 * 0.5}{0.4} $$

$$ P(Defected \mid M_{1}) = 0.0125 $$

$$ P(Defected \mid M_{2}) = \frac{0.01 * 0.5}{0.6} $$

$$ P(Defected \mid M_{2}) = 0.075 $$

### Naive Bayes Classifier

This classifier usages Bayes Theorem to predict the class of new data point

$$ P(A \mid B) = \frac{P(B \mid A) \cdot P(A)}{P(B)} $$

This Classification works in three step

Step 1) Find the probability that new datapoint belongs to class A

Step 2) Find the probability that new datapoint belongs to class B

Step 3) Compare probabilities and predict the class of new data point.

Given a set of datapoints, Red and Green. Find the class of new datapoint (Gray).
<img src="./Classification/Naive_Bayes_Classifier/problem_statement.png">

**Step 1 : Calculate P(Walks|X)**
<img src="./Classification/Naive_Bayes_Classifier/Step_1.1.png">

1. P(Walks) [ Prior Probability ]
<img src="./Classification/Naive_Bayes_Classifier/Step_1.2.png">

2. P(X|Walks) [ Likelihood ]
: Draw a circle around the new data point, **Observation Circle**
<img src="./Classification/Naive_Bayes_Classifier/Step_1.3.png">

3. P(X) [ Marginal Likelihood ]
<img src="./Classification/Naive_Bayes_Classifier/Step_1.4.png">

4. P(Walks|X) [ Posterior Probability ]
<img src="./Classification/Naive_Bayes_Classifier/Step_1.5.png">

**Step 2 : Calculate P(Drives|X)**
<img src="./Classification/Naive_Bayes_Classifier/Step_2.png">

**Step 3 : Compare P(Walks|X) and P(Drives|X)**
<pre>
P(Walks|X) v.s. P(Drives|X)
0.75 v.s. 0.25
0.75 > 0.25
</pre>

**It means the new datapoint is going to Red Class**

In the Step 3

$$ P(Walks \mid X) \  \  v.s. \  \  P(Drives \mid X) $$

$$ \frac { P(X \mid Walks) \cdot P(Walks)} {P(X)} \  \  v.s. \  \  \frac { P(X \mid Drives) \cdot P(Drives)} {P(X)} $$

P(X) can be discarded

$$ \frac { P(X \mid Walks) \cdot P(Walks)} { \xcancel{P(X)} } \  \  v.s. \  \  \frac { P(X \mid Drives) \cdot P(Drives)} {\xcancel{P(X)} } $$

$$ P(X \mid Walks) \cdot P(Walks) \  \  v.s. \  \  P(X \mid Drives) \cdot P(Drives) $$


### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Naive_Bayes_Classification/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Naive Bayes Classifier Model using Training Data

```python
from sklearn.naive_bayes import GaussianNB
classifier = GaussianNB()
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title(' Naive Bayes Classifier  (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title(' Naive Bayes Classifier  (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```


## Decision Tree Classification

In the below set of data points, we can use some filters to draw a decision tree, and decide the color/class of new data point

<img src="./Classification/Decision_Tree_Classification/DTC_datapoints.png" />

The generated decision tree will be

<img src="./Classification/Decision_Tree_Classification/DTC_decision_tree.png" />


### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Decision_Tree_Classification/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Decision Tree Classification Model using Training Data

```python
from sklearn.tree import DecisionTreeClassifier
classifier = DecisionTreeClassifier(criterion = 'entropy', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title(' Decision Tree Classification  (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title(' Decision Tree Classification  (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

## Random Forest Classification

<img src="./Classification/Random_Forest_Classification/RF_steps.png"/>


### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Random_Forest_Classification/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Random Forest Classification Model using Training Data

```python
from sklearn.tree import DecisionTreeClassifier
classifier = DecisionTreeClassifier(criterion = 'entropy', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Random Forest Classification  (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(iRandom Forest Classification), label = j)
plt.title('  (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

<br/>
<hr/>
<br/>

> # Selecting best classification model

## Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Model_Selection_Classification/Data.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

## Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit Score of  training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```

## Training the Classification Models Score of  Training Data

```python
# Using Logisitic Regression Classification
from sklearn.linear_model import LogisticRegression
classifier = LogisticRegression(random_state = 0)
classifier.fit(X_train,y_train)
y_pred_LR = classifier.predict(X_test)

# Using K-Nearest Neighbor Classification
from sklearn.neighbors import KNeighborsClassifier
classifier = KNeighborsClassifier(n_neighbors = 5, metric = "minkowski", p = 2)
classifier.fit(X_train,y_train)
y_pred_KNN = classifier.predict(X_test)

# Using Support Vector Classification
from sklearn.svm import SVC
classifier = SVC(kernel = 'linear', random_state = 0)
classifier.fit(X_train,y_train)
y_pred_SVC = classifier.predict(X_test)

# Using Kernel SVM Classification
from sklearn.svm import SVC
classifier = SVC(kernel = 'rbf', random_state = 0)
classifier.fit(X_train,y_train)
y_pred_KSVM = classifier.predict(X_test)


# Using Naive Bayes Classification
from sklearn.naive_bayes import GaussianNB
classifier = GaussianNB()
classifier.fit(X_train,y_train)
y_pred_NB = classifier.predict(X_test)


# Using Decision Tree Classification
from sklearn.tree import DecisionTreeClassifier
classifier = DecisionTreeClassifier(criterion = 'entropy', random_state = 0)
classifier.fit(X_train,y_train)
y_pred_DT = classifier.predict(X_test)


# Using Random Forest Classification
from sklearn.tree import DecisionTreeClassifier
classifier = DecisionTreeClassifier(criterion = 'entropy', random_state = 0)
classifier.fit(X_train,y_train)
y_pred_RF = classifier.predict(X_test)
```

## Making the Confusion Matrix and comparing the models

```python
from sklearn.metrics import confusion_matrix, accuracy_score
Score =[]

# Using Logisitic Regression Classification
cm = confusion_matrix(y_test,y_pred_LR)
acs = accuracy_score(y_test,y_pred_LR)
Score.append(["Logistic Regression Classification", cm, acs])

# Using K-Nearest Neighbor Classification
cm = confusion_matrix(y_test,y_pred_KNN)
acs = accuracy_score(y_test,y_pred_KNN)
Score.append(["K-Nearest Neighbor Classification", cm, acs])

# Using Support Vector Classification
cm = confusion_matrix(y_test,y_pred_SVC)
acs = accuracy_score(y_test,y_pred_SVC)
Score.append(["Support Vector Classification", cm, acs])

# Using Kernel SVM Classification
cm = confusion_matrix(y_test,y_pred_KSVM)
acs = accuracy_score(y_test,y_pred_KSVM)
Score.append(["Kernel SVM Classification", cm, acs])


# Using Naive Bayes Classification
cm = confusion_matrix(y_test,y_pred_NB)
acs = accuracy_score(y_test,y_pred_NB)
Score.append(["Naive Bayes Classification", cm, acs])


# Using Decision Tree Classification
cm = confusion_matrix(y_test,y_pred_DT)
acs = accuracy_score(y_test,y_pred_DT)
Score.append(["Decision Tree Classification", cm, acs])


# Using Random Forest Classification
cm = confusion_matrix(y_test,y_pred_RF)
acs = accuracy_score(y_test,y_pred_RF)
Score.append(["Random Forest Classification", cm, acs])



for score in Score:
    print(score[0],":",score[2])
    print("Confusion matrix")
    print(score[1])
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```


## Evaluating Model Performances

### False Positive and False Negative

<img src="./Classification/Evaluating_Model_Performances/False_Positive_False_Negative.png"/>

### Confusion Matrix

<img src="./Classification/Evaluating_Model_Performances/Confusion_Matrix.png"/>


### Accuracy Paradox

<img src="./Classification/Evaluating_Model_Performances/Accuracy_Paradox_1.png"/>

Now if in this scenario we only predict 0, means replace every 1 with 0 in prediction, the resultant accuracy rate will be

<img src="./Classification/Evaluating_Model_Performances/Accuracy_Paradox_2.png"/>

This is known as **Accuracy Paradox**, Accuracy rate shows that the accuracy of model is increased, but in actual it's getting vorse.

### Cap Curve

Suppose we have a list of customer data [Who purchased, who not purchased], according to data only 10% customer purchased the product.

Now in the below diagram

<img src="./Classification/Evaluating_Model_Performances/CAP_1.png"/>

- Blue Line : Randomly sent advertisement/invitation to the all customer.
- Green Line : Using some classification/regression algorithm, advertisement/invitation were sent to only those customer, who can purchase the product.
- Red Line : Using best classification/regression model, advertisement/invitation were sent to only those customer, who can purchase the product.
- Gray Line : If it was already known, who is goin to purchase the product, and advertisement/invitation is sent only those customers.


<img src="./Classification/Evaluating_Model_Performances/CAP_2.png"/>

### CAP Analysis

Now using CAP curve
<img src="./Classification/Evaluating_Model_Performances/CAP_Analysis_1.png"/>

#### a<sub>P</sub> : Area under the Random model and Perfect Model

#### a<sub>R</sub> : Area under the Random model and Good Model

$$ AR = \frac{a_{R}} {a_{P}} $$

The above method to compute Accuracy Rate, is very complex because finding area under the curve is a complex process.

There exist one more method to calculate AR

<img src="./Classification/Evaluating_Model_Performances/CAP_Analysis_2.png"/>

> Note : X > 90%, means model is over fitted. 

## Classification Pros and Cons

<img src="./Classification/Evaluating_Model_Performances/Classification_Pros_Cons.png"/>

<br/>
<hr/>
<br/>

> # Clustering

Clustering is a technique, to make some new groups/cluster from a given data points.

## K-Mean Clustering

<img src="./Clustering/K_Mean_Clustering/K_Mean_1.png" />

**Steps for the K-Mean Clustering**

<img src="./Clustering/K_Mean_Clustering/K_Mean_Steps.png" />

Let's apply above algorithm on a set of data points, and take K as 2.

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_1.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_2.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_3.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_4.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_5.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_6.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_7.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_8.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_9.png"/>

<img src="./Clustering/K_Mean_Clustering/K_Mean_Step_10.png"/>

In this way, the K-Mean Clustering works.

**Random Initialization Trap : If somehow we select very bad initial K centroids, the result may vary. To avoid this issue instead of K-Mean Clustering , K-Mean++ Clustering is used.**

### Choosing right number of cluster [The Elbow Technique]

In any dataset, we can have minimum one cluster, and maximum N cluster, N is the total data points.

In the first step we need to select the value of K, For better selection we can use **Within Cluster Sum of Squares (WCSS)** technique

$$ WCSS = \sum_{i=1}^{K} \sum_{j=1}^{N_{i}} Distance(C_{i},P_{ij})^{2} $$

$$ K : No \ \  of \ Clusters $$

$$ N_{i} :  No \ \  of \ Points \  inside \ i^{th} \  Cluster $$

$$ C_{i} : Centroid \ \  of \ i^{th} \  Cluster $$

$$ P_{ij} :  j^{th} \ Point \ \  inside \ i^{th} \  Cluster $$

For below datapoints

- K = 1
<img src="./Clustering/K_Mean_Clustering/Choose_K_1.png"/>
- K = 2
<img src="./Clustering/K_Mean_Clustering/Choose_K_2.png"/>
- K = 3
<img src="./Clustering/K_Mean_Clustering/Choose_K_3.png"/>

As we increase K, value of WCSS keeps decreasing, **Inversly Proportinal**

$$ WCSS \propto \frac {1} {K} $$

Below is the graph between **WCSS vs K**

<img src="./Clustering/K_Mean_Clustering/WCSS_Graph.png"/>

The shape of the graph is very simillar to a human hand, and it was found that the point near elbow of the graph is the best value of K.

<img src="./Clustering/K_Mean_Clustering/WCSS_Graph_Elbow.png"/>

### Data Preprocessing

```python
# Data Preprocessing

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Clustering/K_Mean_Clustering/Mall_Customers.csv')

X = dataset.iloc[:,[3,4]].values

print(X)
```

### The Elbow Method

```python
from sklearn.cluster import KMeans
wcss = []
for i in range(1,11):
    kmeans = KMeans(n_clusters = i, init = 'k-means++', random_state = 42)
    kmeans.fit(X)
    wcss.append(kmeans.inertia_)
plt.plot(range(1,11),wcss)
plt.title("The Elbow Method")
plt.xlabel("Number of Clusters")
plt.ylabel("WCSS")
plt.show()
'''
From below graph, it is clear that K = 5 is the optimal value
'''
```

### Training the K-Means Clustering Model on Training Dataset

```python
K = 5
kmeans = KMeans(n_clusters = K, init = 'k-means++', random_state = 42)
y_kmeans = kmeans.fit_predict(X)
print(y_kmeans)
```

### Visualizing the cluster

```python
plt.scatter(X[y_kmeans == 0, 0], X[y_kmeans == 0, 1], s = 50, c = 'red', label =  'Cluster 1')
plt.scatter(X[y_kmeans == 1, 0], X[y_kmeans == 1, 1], s = 50, c = 'blue', label =  'Cluster 2')
plt.scatter(X[y_kmeans == 2, 0], X[y_kmeans == 2, 1], s = 50, c = 'green', label =  'Cluster 3')
plt.scatter(X[y_kmeans == 3, 0], X[y_kmeans == 3, 1], s = 50, c = 'cyan', label =  'Cluster 4')
plt.scatter(X[y_kmeans == 4, 0], X[y_kmeans == 4, 1], s = 50, c = 'magenta', label =  'Cluster 5')
plt.scatter(kmeans.cluster_centers_[:,0], kmeans.cluster_centers_[:,1], s = 100, c = 'yellow', label = 'Centroids')

plt.title("Clusters of Customers")
plt.xlabel("Anual Income (k$) ")
plt.ylabel("Spending Score (0-100)")
plt.legend()
plt.show()
```

## Hierarchical Clustering

Output will be simillar to the K-Means Clustering, but process is different

Types of Hierarchical Clustering
1. Agglomerative Hierarchical Clustering
2. Divisive Hierarchical Clustering

### Agglomerative Hierarchical Clustering

<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_steps.png" />

<img src="./Clustering/Hierarchical_Clustering/Distance_BW_Clusters.png" />

Let's apply Agglomerative Hierarchical Clustering steps on below data points
<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_0.png" />




<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_1.png" />


<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_2.png" />


<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_3.png" />


<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_4.png" />


<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_5.png" />


<img src="./Clustering/Hierarchical_Clustering/Agglomerative_HC_step_6.png" />

**Agglomerative Clustering** remembers the process by which one huge cluster is created, this process is stored in the memory in the form of **Dendrograms**.

> ### Dendrograms
These are basically a graph simillar to bar chart that is plotted b/w datapoints/clusters vs Eucledian Distance b/w datapoints/clusters.

### How to Draw Dendrograms
Let's convert below datpoints/clusters into Dendrograms
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_0.png" />

- [ P<sub>2</sub> ] + [ P<sub>3</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_1.png" />
**Height of any bar is the Eucledian Distance/Disimilarity b/w the two clusters**

- [ P<sub>5</sub> ] + [ P<sub>6</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_2.png" />

- [ P<sub>2</sub>, P<sub>3</sub> ] + [ P<sub>1</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_3.png" />

- [ P<sub>5</sub>, P<sub>6</sub> ] + [ P<sub>4</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_4.png" />

- [ P<sub>1</sub>, P<sub>2</sub>, P<sub>3</sub> ] + [ P<sub>4</sub>, P<sub>5</sub>, P<sub>6</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_5.png" />

And Finally,
- [ P<sub>1</sub>, P<sub>2</sub>, P<sub>3</sub>, P<sub>4</sub>, P<sub>5</sub>, P<sub>6</sub> ]
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_6.png" />


### How to Use Dendrograms

Let's assume all the bars have their horizontal line, starting from 0, then our dendrogram will look like
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_HL.png" />

Now we have two types of lines in the graph
1. Horizontal lines
2. Vertical lines

Select Longest vertical line, that is not crossing any Horizontal line, reference vertical line.
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_HLM.png" />

Now, draw a Horizontal line from the center of  reference vertical line and extend it from 0 to max, this new Horizontal line is basically the maximum allowed Disimilarity between clusters. let's say it reference horizontal line.
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_V_HL.png" />

Now, no of vertical lines that are crossed by the reference horizontal line, are the no of cluster for the given datapoints
<img src="./Clustering/Hierarchical_Clustering/Dendrograms_2_CL.png" />

We are getting two cluster for above datasets, where maximum allowed disimilarity is 1.7.


<img src="./Clustering/Hierarchical_Clustering/Dendrograms_2_CL.png" />

We are getting three cluster for above datasets, where maximum allowed disimilarity is 2.5.

### Data Preprocessing
```python
# Data Preprocessing

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Clustering/Hierarchical_Clustering/Mall_Customers.csv')

X = dataset.iloc[:,[3,4]].values

print(X)
```

### Using the Dendrograms methods, to find optimal value of K
```python
import scipy.cluster.hierarchy as sch # new library for dendrograms
dendrogram = sch.dendrogram(sch.linkage(X, method = 'ward')) # ward -> minimum variance technique
plt.axhline(y=350) # line 1 
plt.axhline(y=150) # line 2
plt.title("Dendrogram")
plt.xlabel("Customers")
plt.ylabel("Euclidean Distance")
plt.show()

'''
Either we can take the third blue vertical line y=350 , or the third orange lines, y=150, as both looks largest
Let's choose the third orange vertical line y=150
From below graph, it is clear that K = 5 is the optimal value
'''

print()
```

### Training the Hierarchical Clustering Model on Training Dataset
```python
from sklearn.cluster import AgglomerativeClustering
hc = AgglomerativeClustering(n_clusters = 5, affinity = 'euclidean', linkage = 'ward')
y_hc = hc.fit_predict(X)
print(y_hc)
```

### Visualizing the cluster
```python
plt.scatter(X[y_hc == 0, 0], X[y_hc == 0, 1], s = 50, c = 'red', label =  'Cluster 1')
plt.scatter(X[y_hc == 1, 0], X[y_hc == 1, 1], s = 50, c = 'blue', label =  'Cluster 2')
plt.scatter(X[y_hc == 2, 0], X[y_hc == 2, 1], s = 50, c = 'green', label =  'Cluster 3')
plt.scatter(X[y_hc == 3, 0], X[y_hc == 3, 1], s = 50, c = 'cyan', label =  'Cluster 4')
plt.scatter(X[y_hc == 4, 0], X[y_hc == 4, 1], s = 50, c = 'magenta', label =  'Cluster 5')

plt.title("Clusters of Customers")
plt.xlabel("Anual Income (k$) ")
plt.ylabel("Spending Score (0-100)")
plt.legend()
plt.show()
```

<br/>
<hr/>
<br/>

> # Association Rule Learning
let's take below statements
<pre>
Person Who watched Movie1 also watches Movie2.

Person Who bought product1 also buys product2.
</pre>

The above two statement are in the form 

$$ S_{1} \rightarrow S_{2} $$

<img src="./Association_Rule_Learning/Movie_Recommendation.png"/>

<img src="./Association_Rule_Learning/Product_Recommendation.png"/>

This type of statement are know as **Association Rule** , Basically we are associating S<sub>2</sub> with S<sub>1</sub>.

These type of rules basically help in recommendation system.

## Apriori Algorithim

Let's take a Movie watch history data for 100 peoples.
<img src="./Association_Rule_Learning/Apriori_Algorithm/Movie_DATA.png"/>
Red marked - watched Movie M<sub>1</sub>

Green - watched Movie M<sub>2</sub>



### Apriori Support
<img src="./Association_Rule_Learning/Apriori_Algorithm/Apriori_Support.png"/>
If out of 100 peoples, 10 watched Movie M<sub>1</sub>, then

$$ Apriori \ Support \ for \ M_{1} = \frac{10}{100} = 10% $$

### Apriori Confidence
<img src="./Association_Rule_Learning/Apriori_Algorithm/Apriori_Confidence.png"/>
If out of 100 peoples, 40 watched Movie M<sub>2</sub>, and out of these 40, only 7 watched M<sub>1</sub> and M<sub>2</sub>

$$ Apriori \ Confidence \ for \ M_{1} \rightarrow M_{2} = \frac{7}{40} = 17.5% $$


### Apriori Lift
<img src="./Association_Rule_Learning/Apriori_Algorithm/Apriori_Lift.png"/>
Now suppose for a new population, if you directly recommend peoples to watch Movie M<sub>1</sub>, then there is a chance of only 10%, but if you ask first whether they have watched M<sub>2</sub> and based on the answer you recommend M<sub>1</sub>, then there is a chance of 17.5%.

This is known as Apriori Lift.

$$ Apriori \ Lift \ for \ M_{1} \rightarrow M_{2} = \frac{17.5\%}{10\%} = 1.75% $$

**Steps for Apriori Algoritnms**

<img src="./Association_Rule_Learning/Apriori_Algorithm/Apriori_Steps.png"/>

```python
# Importing Libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Importing Datasets
dataset = pd.read_csv("./Datasets/Market_Basket_Optimisation.csv", header = None)

transactions = []
for i in range(dataset.shape[0]):
    transactions.append([str(dataset.values[i, j]) for j in range(dataset.shape[1])])

# print(transactions)
```

### Training Apriori Model on the dataset

```python
from apyori import apriori
rules = apriori(transactions = transactions, min_support = 0.003, min_confidence = 0.2, min_lift = 3, min_length = 2, max_length = 2)
```

### Visualizing the results

#### Displaying the firsts result directly comming from apriori funtion
```python
results = list(rules)
print(results)
```

#### Putting the results well organised into a pandas dataframe
```python
def inspect(results):
    lhs         = [tuple(result[2][0][0])[0] for result in results]
    rhs         = [tuple(result[2][0][1])[0] for result in results]
    supports    = [result[1] for result in results]
    confidences = [result[2][0][2] for result in results]
    lifts       = [result[2][0][3] for result in results]
    return list(zip(lhs, rhs, supports, confidences, lifts))
resultsinDataFrame = pd.DataFrame(inspect(results), columns = ['Left Hand Side', 'Right Hand Side', 'Support', 'Confidence', 'Lift'])
```

#### Displaying the result non sorted
```python
print(resultsinDataFrame)
```

#### Displaying the result in descending order by Lift
```python
print(resultsinDataFrame.nlargest(n=10,columns = 'Lift'))
```


## ECLAT Association Rule Learning

Eclat, is very simillar to Apriori Algorithm. It is a simpler form of Apriori Algorithm.

This also works as a recommendation system.

In Apriori Algorithm, we work on potential rules

$$ A \rightarrow B  $$

However, in ECLAT, we basically work on sets, So if we have,

$$ S_{1} = \{ A,B,C \} $$
$$ S_{2} = \{ A,B,D \} $$
$$ S_{3} = \{ C,E,D \} $$
$$ S_{4} = \{ A,E,B \} $$
$$ S_{5} = \{ A,B \} $$

On the basis of above 6 sets, we can see A and B are 100% times in the same set, So we can Reccomend A and B together.

In Eclat, we only have Support, **Eclat Support**

<img src="./Association_Rule_Learning/Eclat/Eclat_Support.png" />

**Where M and I are set of items**

Steps for Eclat

<img src="./Association_Rule_Learning/Eclat/Eclat_Steps.png" />


```python
# Importing Libraries
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Importing Datasets
dataset = pd.read_csv("./Datasets/Market_Basket_Optimisation.csv", header = None)

transactions = []
for i in range(dataset.shape[0]):
    transactions.append([str(dataset.values[i, j]) for j in range(dataset.shape[1])])

# print(transactions)
```

### Training Eclat Model on the dataset

```python
from apyori import apriori
rules = apriori(transactions = transactions, min_support = 0.003, min_confidence = 0.2, min_lift = 3, min_length = 2, max_length = 2)
```

### Visualizing the results

#### Displaying the firsts result directly comming from apriori funtion
```python
results = list(rules)
print(results)
```

#### Putting the results well organised into a pandas dataframe
```python
def inspect(results):
    lhs         = [tuple(result[2][0][0])[0] for result in results]
    rhs         = [tuple(result[2][0][1])[0] for result in results]
    supports    = [result[1] for result in results]
    return list(zip(lhs, rhs, supports))
resultsinDataFrame = pd.DataFrame(inspect(results), columns = ['Product 1', 'Product 2', 'Support'])
```

#### Displaying the result non sorted
```python
print(resultsinDataFrame)
```

#### Displaying the result in descending order by Support
```python
print(resultsinDataFrame.nlargest(n=10,columns = 'Support'))
```


<br>
<hr/>
<br/>

# Reinforcement Learning

## The Multi Arm Bandit Problem
Suppose you have 10 ads for a product, now you distribute yours ads for the advertisement. You are randomly, distributing your ads, but this is not an efficient way, you should have the distribution according to the audience preference, So you must know which ads is good, and which is not. 

<img src="./Reinforcement_Learning/The_Multi_Armed_Bandit_Problem.png"/>

## Upper Confiednce Bound Algorithm
<img src="./Reinforcement_Learning/Upper_Confiednce_Bound_Algorithm/Upper_Confiednce_Bound_Algorithm.png"/>

### importing modules and Datasets
```python
# importing modules and Datasets
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset = pd.read_csv("./Datasets/Ads_CTR_Optimisation.csv")
X =  dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)
```

### Implementing Upper Confidence Bound (UCB)
```python
import math
N = dataset.shape[0] #10000
d = dataset.shape[1] #10
ads_selected = []
no_of_selections = [0] * d
sum_of_rewards =[0] * d
total_reward = 0
for n in range(N):
    ad = 0
    max_upper_bound = 0
    for i in range(d):
        if no_of_selections[i] > 0:
            average_reward = sum_of_rewards[i] / no_of_selections[i]
            delta_i = math.sqrt((3*math.log(n+1))/(2*no_of_selections[i]))
            upper_bound = average_reward + delta_i
        else:
            upper_bound = 1e400
        
        if upper_bound > max_upper_bound :
            max_upper_bound = upper_bound
            ad = i
    ads_selected.append(ad)
    reward = dataset.values[ n, ad]
    no_of_selections[ad] += 1
    sum_of_rewards[ad] += reward
    total_reward += reward
```

### Visualize the result
```python
plt.hist(ads_selected)
plt.title('Histogram of ads selection')
plt.xlabel('Ads')
plt.ylabel('No of times each ads selected')
plt.show()
```

## Thompson Sampling Algorithm

<img src="./Reinforcement_Learning/Thompson_Sampling_Algorithm/Bayesian_Inference.png"/>

<img src="./Reinforcement_Learning/Thompson_Sampling_Algorithm/Thompson_Sampling.png"/>

### Importing modules and Datasets
```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset = pd.read_csv("./Datasets/Ads_CTR_Optimisation.csv")
X =  dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)
```

### Implementing Thompson Sampling Algorithm
```python
import random
N = dataset.shape[0] #10000
d = dataset.shape[1] #10
ads_selected = []
no_of_rewards_1 = [0] * d
no_of_rewards_0 = [0] * d
total_reward = 0
for n in range(N):
    ad = 0
    max_random = 0
    for i in range(d):
        random_beta = random.betavariate(no_of_rewards_1[i] + 1, no_of_rewards_0[i] + 1)
        if random_beta > max_random:
            max_random = random_beta
            ad = i
    ads_selected.append(ad)
    reward = dataset.values[n,ad]
    if reward == 0:
        no_of_rewards_0[ad]+=1
    else:
        no_of_rewards_1[ad]+=1
    total_reward += reward
```

### Visualize the results
```python
plt.hist(ads_selected)
plt.title('Histogram of ads selection')
plt.xlabel('Ads')
plt.ylabel('No of times each ads selected')
plt.show()
```


## Upper Confidence Bound vs Thompson Sampling

<img src="./Reinforcement_Learning/Upper_Confidence_Bound_vs_Thompson_Sampling.png"/>

<br/>
<hr/>
<br/>

# Natural Language Processing

<img src="./Natural_Language_Processing/Type_of_NLP.png"/>

<img src="./Natural_Language_Processing/Examples.png"/>

## Bag of Words
According to google, native adult speakers of English understand an average of 20,000 to 30,000 vocabulary words.
<img src="./Natural_Language_Processing/Google_Search.png"/>
Let's assume we have an array/list of 20,000 size, we can put all the words at different index and hence we can make a difeerent 20,000 sized array for any statement in the world,

$$ A = [0,0,0,0,0,0,0,0,...,0] \ \ \ \ i.e. \ \ \ 20000  \ \ sized \ \ array $$

For below sentence this Array will look like
<img src="./Natural_Language_Processing/Sample_Array.png"/>

For simplicity, let's consider answering questions using NLP as Yes/No
<img src="./Natural_Language_Processing/Sample_Questions_Answers.png"/>

<img src="./Natural_Language_Processing/Bag_of_Words.png"/>

### Importing modules and Datasets
```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

dataset = pd.read_csv("./Datasets/Restaurant_Reviews.tsv", delimiter="\t", quoting=3) # quoting=3 ignore "
print(dataset)
```


### Cleaning the Texts
for cleaning the texts we need two more libraries
- re: for regular expression 
- nltk: Natural Language Tool Kit, for all the cleaning

Cleaning of Texts means, removing all the words that are irrelevent for our purpose, for example the,a, of etc. are not needed for review analysis

Steps for cleanng
1. Downloading the stopwords using nltk
2. Removing all the punctuations
3. Convert in lowercase and split them in a list with delimeter as space
4. Converting the tenses to present tense
5. Join them by space
6. Cleaning complete

```python
import re
import nltk
nltk.download("stopwords")
from nltk.corpus import stopwords
from nltk.stem.porter import PorterStemmer
N, m = dataset.shape
corpus = []
for i in range(N):
    review = re.sub("[^a-zA-Z]", " ", dataset['Review'][i])
    review = review.lower()
    review = review.split()
    ps = PorterStemmer()
    all_stopwords = stopwords.words('english')
    all_stopwords.remove("not")
    review = [ps.stem(word) for word in review if word not in set(all_stopwords)]
    review = ' '.join(review)
    corpus.append(review)
print(corpus)
```

### Making Bag of Words Model
The above cleaning method has cleaned most of the things, but there are some more words that are irrelevent for analysis, to remove them we use CountVectorizer, this will take only the frequest words from all the words and create an array of size(N=20,000) for our analysis

```python
from sklearn.feature_extraction.text import CountVectorizer
cv = CountVectorizer()
X = cv.fit_transform(corpus).toarray()
y = dataset.iloc[:,-1].values
print(X)
print(len(X),len(X[0]))
print(y)
print(len(y))
```

### Splitting dataset into train and test set
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Training the Naive Bayes Classifier Model using Training Data
```python
from sklearn.naive_bayes import GaussianNB
classifier = GaussianNB()
classifier.fit(X_train,y_train)
```

### Predict Test results
```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix
```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```


<br/>
<hr/>
<br/>

# Deep Learning
In this we try to mimic the human brain [neural network], Using some layers
- Input Layer:Input
- Hidden Layer: Process
- Output Layer: Output

<img src="./Deep_Learning/Deep_learning.png"/>

## Artificial Neural Network [ ANN ]

### The Neuron
Below is the diagram of human neuron
<img src="./Deep_Learning/Artificial_Neural_Network/Human_neuron.png"/>

- Dendrites : Receiver of the Signals
- Axon : Transmitter of the Signal
- Neuron : Process the Signal

Below is the actual image of Human Neurons
<img src="./Deep_Learning/Artificial_Neural_Network/Human_neurons.png"/>

Below is the diagram of Artificial Neuran
<img src="./Deep_Learning/Artificial_Neural_Network/Artificial_neuron.png"/>

From diagram we can say that there are three layers
- Input Layer : For Input
- Neuron : For Processing
- Output Layer : For Output

Now in Input Layer, we have two things
- Input : The Input Signal, X<sub>1</sub>, X<sub>2</sub>
- Weight : Importance of the input signal, w<sub>1</sub>, w<sub>2</sub>

In Neuron, Following steps are performed
1. Calculating Weighted Sum
$$ R = \sum_{i=1}^{m} X_{i}*w_{i} $$

2. Applying Activation Function
$$ y = \phi (R) $$

3. Pass the result to output Layer

In output layer, we have output y, and y can be a
- Continious Data (Price)
- Binary Data (Yes/No)
- Categorial Data (C<sub>1</sub>, C<sub>1</sub>)

### The Activation Function
1. Threshold Activation Function
<img src="./Deep_Learning/Artificial_Neural_Network/Threshold_activation_function.png"/>

2. Sigmoid Activation Function
<img src="./Deep_Learning/Artificial_Neural_Network/Sigmoid_activation_function.png"/>

3. Rectifier Activation Function
<img src="./Deep_Learning/Artificial_Neural_Network/Rectifier_activation_function.png"/>

4. Hyperbolic Tangent Activation Function
<img src="./Deep_Learning/Artificial_Neural_Network/Hyperbolic_tangent_activation_function.png"/>

Combination of Rectifier and Sigmoid Function
<img src="./Deep_Learning/Artificial_Neural_Network/Rectifier_sigmoid_activation_function.png"/>


### Working of Neural Networks
Let's see an example of property price evaluation using NNs

- Without Hidden Layer
<img src="./Deep_Learning/Artificial_Neural_Network/Without_hidden_layer.png"/>

- With Hidden Layer
<img src="./Deep_Learning/Artificial_Neural_Network/With_hidden_layer.png"/>

### Learning of Neural Networks
y : Actual Value

&ycirc; : Output Value

<img src="./Deep_Learning/Artificial_Neural_Network/NN_learning.png"/>
Steps

1. First we put all the data in our NNs, and NN gives us some &ycirc;
2. Next we calculate Cost
$$ C = \frac{1}{2}(\hat{y}-y)^{2} $$
3. Based on the value of C update w<sub>1</sub>, w<sub>2</sub>, and w<sub>3</sub>
4. Repeat the above 3 steps, for minimum cost

Example of NNs Learning
<img src="./Deep_Learning/Artificial_Neural_Network/NN_learning_example.png"/>


### Backpropagation [ Adjusting Weight ]

#### Bruteforce Method

We can select best weights using Brute Force
<img src="./Deep_Learning/Artificial_Neural_Network/Adjusting_weight_brute_force.png"/>

But problem in Bruteforce Method is **Curse of Dimensionality**, means for high dimension, calculation can take more than few billion years.


To overcome this problem **Gradient Descent** is used

#### Batch Gradient Descent

<img src="./Deep_Learning/Artificial_Neural_Network/Adjusting_weight_gradient_descent.png"/>

In Batch Graident Descent, we take all the data in every go, and update waight accordingly, this works only for convex type graph, but for a graph below one, we can have a problem of local minima
<img src="./Deep_Learning/Artificial_Neural_Network/local_minima_problem.png"/>

#### Stochastic Gradient Descent
To overcome the problem of local minima, instead of batch processing, we take one row at a time, and after that we take the 2nd row, this is known as Stochastic Gradient Descent

#### Batch Gradient Descent vs Stochastic Gradient Descent
<img src="./Deep_Learning/Artificial_Neural_Network/Batch_vs_Stochastic_gradient_descent.png"/>

### Training Artificial Neural Network
<img src="./Deep_Learning/Artificial_Neural_Network/ANN_Training.png"/>


### Importing the Libraries and Datasets
```python
import pandas as pd
import numpy as np
import tensorflow as tf

dataset = pd.read_csv("./Datasets/Churn_Modelling.csv")
X = dataset.iloc[:, 3:-1].values
y = dataset.iloc[:, -1].values

print(X)
print(y)
```

### Encoding the Categorial Data
```python
# LabelEncoder for gender
from sklean.preprocessing import LabelEncoder
le = LabelEncoder()
X[:, 2] = le.fit_transform(X[:, 2])

# OneHotEncoding for geography
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[1])], remainder='passthrough')
X = np.array(ct.fit_transform(X))

print(X)
```


### Splitting dataset into train and test set
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling
```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit and transform training data using the scaler
X_train = sc.fit_transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```

### Building the ANN
```python
# Initializing the ANN
ann = tf.keras.models.Sequential()

# Adding the Input and First Hidden Layer
ann.add(tf.keras.layers.Dense(units=6, activation='relu'))

# Adding the Second Hidden Layer
ann.add(tf.keras.layers.Dense(units=6, activation='relu'))

# Adding the Output Layer
ann.add(tf.keras.layers.Dense(units=1, activation='sigmoid'))
```

### Training the ANN
```python
# Compiling the ANN
ann.compile(optimizer = 'adam', loss='binary_crossentropy' , metrics = ['accuracy'])

# Training the ANN on Training set
ann.fit(X_train, y_train, batch_size=32, epochs=100)
```

### Predict for a single test
Use our ANN model to predict if the customer with the following informations will leave the bank: 

Credit Score: 600

Geography: France

Gender: Male

Age: 40 years old

Tenure: 3 years

Balance: \$ 60000

Number of Products: 2

Does this customer have a credit card ? Yes

Is this customer an Active Member: Yes

Estimated Salary: \$ 50000

So, should we say goodbye to that customer ?

```python
# 'france' => 1, 0, 0
# 'Male' => 1
tmp_dataset = [[1, 0, 0, 600, 1, 40, 3, 60000, 2, 1, 1, 50000]]

prob = ann.predict(sc.transform(tmp_dataset))

print(prob)

if prob > 0.5:
    print("Customer will leave the Bank")
else:
    print("Customer will not leave the Bank")
```

### Predicting for the Test Set
```python
y_pred_prob = ann.predict(X_test)
y_pred = (y_pred_prob > 0.5)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix
```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

## Convolution Neural Network [ CNN ]
In the below images

<hr/>

- Image with two Faces 

<img src="./Deep_Learning/Convolution_Neural_Network/Man_with_two_faces.png"/>

    1. Man loooking to the right
    2. Man looking at you

<hr/>

- Lady with two Faces 

<img src="./Deep_Learning/Convolution_Neural_Network/Lady_with_two_ages.png"/>

    1. Girl loooking away
    2. Old lady looking down

<hr/>

- Duck or the Rabit 

<img src="./Deep_Learning/Convolution_Neural_Network/Duck_or_the_rabit.png"/>

    1. Duck
    2. Rabit

<hr/>

- Image with Moving Face 

<img src="./Deep_Learning/Convolution_Neural_Network/Image_with_moving_face.png"/>

    1. Upper one is actual Face
    2. Lower one is actual Face

<hr/>

The above images can looki like 1<sup>st</sup> or the 2<sup>nd</sup>, based on the features on which we are focusing.

<hr/>



How CNN Works?

<img src="./Deep_Learning/Convolution_Neural_Network/CNN_processing.png"/>

CNN Examples

<img src="./Deep_Learning/Convolution_Neural_Network/CNN_example.png"/>

How a computer looks on an image?

<img src="./Deep_Learning/Convolution_Neural_Network/Image_for_computer.png"/>

Steps of CNN

1. Convolution: Detecting the features

    Function for convolution
    $$ (f*g) \overset{\underset{\mathrm{def}}{}}{=} \int_{-\infty}^{\infty} f(\tau) g(t-\tau)d\tau $$

    In graphical view

    <img src="./Deep_Learning/Convolution_Neural_Network/CNN_step_1.png"/>

    This can be understood with the below diagram

    <img src="./Deep_Learning/Convolution_Neural_Network/CNN_step_1_explored.png"/>

    Some common filters

    <img src="./Deep_Learning/Convolution_Neural_Network/Sharpen_filter.png"/>

    <img src="./Deep_Learning/Convolution_Neural_Network/Blur_filter.png"/>

    <img src="./Deep_Learning/Convolution_Neural_Network/Edge_enhance_filter.png"/>

    <img src="./Deep_Learning/Convolution_Neural_Network/Edge_detect_filter.png"/>

    <img src="./Deep_Learning/Convolution_Neural_Network/Emboss_filter.png"/>

    When we apply convolution, we loose some of the patterns of the image, features become linear, so to remove this linearity and imporove our feature/pattern, we apply the rectifier function, **ReLU Layer**

    <img src="./Deep_Learning/Convolution_Neural_Network/ReLU_Layer.png"/>

    Example,

    Original Image

    <img src="./Deep_Learning/Convolution_Neural_Network/Original_image.png"/>

    Image after applying convolution

    <img src="./Deep_Learning/Convolution_Neural_Network/Convolution_applied_image.png"/>

    Now after ReLU Layer

    <img src="./Deep_Learning/Convolution_Neural_Network/ReLU_convolution_applied_image.png"/>


2. Max Pooling : Our object can have different rotation/position/texture in the image, for example

    <img src="./Deep_Learning/Convolution_Neural_Network/Rotated_images.png"/>

    Or, below ones

    <img src="./Deep_Learning/Convolution_Neural_Network/Different_images.png"/>

    
    In Max Pooling, we take a NxN part of the matrix, N can be 2, 3, ... etc. and Now we select the max value of that portion, and we take from left_top to bottom_right, and get a max pooled data.

    Applying Max Pooling to the data after Convolution

    <img src="./Deep_Learning/Convolution_Neural_Network/Max_pooling_process.png"/>

    This will inhance the features, and hence enables to detect object in any rotation, position. Also, this reduces the size of data, hence improve processing.

    There are some other poolings
    1. Sum Pooling
    2. Average Pooling, etc.

    Below is the different layers of Number 4

    <img src="./Deep_Learning/Convolution_Neural_Network/Detect_number_4.png"/>


3. Flattening : Means converting the matrix data into one column [ dimension ]

    Below is the process of flattening

    <img src="./Deep_Learning/Convolution_Neural_Network/Flattening_process.png"/>

    Getting Input Layer

    <img src="./Deep_Learning/Convolution_Neural_Network/Convolution_Input_layer.png"/>

4. Full Connection: It is the step after flattening the data (getting the input layer)

    <img src="./Deep_Learning/Convolution_Neural_Network/Full_connection_process.png"/>

    Detect Cat and Dog

    <img src="./Deep_Learning/Convolution_Neural_Network/Detect_cat_dog.png"/>

    In Backpropagation, hidden layers and the feature detection matrix bot gets modified.

    Detect Dog

    <img src="./Deep_Learning/Convolution_Neural_Network/Detect_dog.png"/>

    Detect Cat

    <img src="./Deep_Learning/Convolution_Neural_Network/Detect_cat.png"/>

    Detection Examples

    <img src="./Deep_Learning/Convolution_Neural_Network/Detection_examples.png"/>

### Complete CNN Process

<img src="./Deep_Learning/Convolution_Neural_Network/Complete_CNN.png"/>

### Softmax
Output of neurons is basically a real number, now to convert them to probability, **Softmax function** is applied.

$$  f_{j}(z) = \frac{e^{z_{j}}}{\sum_{k}^{} e^{z_{k}}} $$

### Cross Entropy

Cost Function are used to evaluate the Neural Network Accuracy/Error, in ANN we used Mean Squared Error Method to calculate the cost

$$ C = \frac{1}{2} (\hat{y}-y)^{2} $$

Cross Entropy is also a cost function and it is better in case of classification, for regression MSE is better.

Function for Cross Entropy

$$ L_{i} = -\log \left ( \frac {e^{f_{y_{i}}}}{\sum_{j}^{ }e^{f_{j}}} \right ) $$

Simplified Cross Entropy Function

$$ H(p,q) = \sum_{x}^{} p(x) \log q(x) $$

Example of Applying Cross Enropy

<img src="./Deep_Learning/Convolution_Neural_Network/Cross_entropy_example.png"/>

Let's suppose two neural networks NN1 and NN2, below is the predictions of cat dog detection using NN1 and NN2

<img src="./Deep_Learning/Convolution_Neural_Network/NN1_NN2.png"/>

Now let's compare them

<img src="./Deep_Learning/Convolution_Neural_Network/NN1_vs_NN2.png"/>


### Importing the Libraries
```python
import tensorflow as tf
from keras.preprocessing.image import ImageDataGenerator
```

### Data Preprocessing [ Image Augmentation ]
```python
# Preprocessing the Training set
train_datagen = ImageDataGenerator(
    rescale = 1./255,
    shear_range = 0.2,
    zoom_range = 0.2,
    horizontal_flip = True
)

training_set = train_datagen.flow_from_directory(
    './Datasets/dataset/training_set/',
    target_size = (64, 64),
    batch_size = 32,
    class_mode = 'binary'
)

# Preprocessing the Test set
test_datagen = ImageDataGenerator(rescale = 1./255)

test_set = train_datagen.flow_from_directory(
    './Datasets/dataset/test_set/',
    target_size = (64, 64),
    batch_size = 32,
    class_mode = 'binary'
)
```

### Building the CNN
```python
# Initialising the CNN
cnn = tf.keras.models.Sequential()

# Step-1 Convolution
cnn.add(
    tf.keras.layers.Conv2D(
        filters = 32,
        kernel_size = 3,
        activation = 'relu',
        input_shape = [64,64,3]
        )
    )

# Step-2 Pooling
cnn.add(
    tf.keras.layers.MaxPool2D(
        pool_size = 2,
        strides = 2
        )
    )

# Step-3 Adding one more Convolution Layer and Pooling
cnn.add(
    tf.keras.layers.Conv2D(
        filters = 32,
        kernel_size = 3,
        activation = 'relu'
        )
    )

cnn.add(
    tf.keras.layers.MaxPool2D(
        pool_size = 2,
        strides = 2
        )
    )

# Step-4 Flattening
cnn.add(tf.keras.layers.Flatten())

# Step-5 Full Connection
cnn.add(
    tf.keras.layers.Dense(
        units = 128,
        activation = 'relu',
    )
)

# Step-6 Output Layer
cnn.add(
    tf.keras.layers.Dense(
        units = 1,
        activation = 'sigmoid',
    )
)
```

### Training the CNN
```python
# Compiling the CNN
cnn.compile(
    optimizer = 'adam',
    loss = 'binary_crossentropy',
    metrics = ['accuracy']
    )

# Training the CNN on Training set and Evaluating on Test set
cnn.fit(
    x = training_set,
    validation_data = test_set,
    epochs = 25
    )
```

### Making a single prediction
```python
import numpy as np
from tensorflow.keras.utils import load_img, img_to_array 

test_image = load_img(
    'Datasets/dataset/single_prediction/cat_or_dog_1.jpg',
    target_size = (64, 64)
)

test_image = img_to_array(test_image)

test_image = np.expand_dims(test_image, axis = 0)

result = cnn.predict(test_image)

training_set.class_indices 

if result[0][0] == 1:
    prediction = 'Dog'
else:
    prediction = 'Cat'
    
print("Input Image contains a", prediction)
```

### Making one more prediction
```python
import numpy as np
from tensorflow.keras.utils import load_img, img_to_array 

test_image = load_img(
    'Datasets/dataset/single_prediction/cat_or_dog_2.jpg',
    target_size = (64, 64)
)

test_image = img_to_array(test_image)

test_image = np.expand_dims(test_image, axis = 0)

result = cnn.predict(test_image)

training_set.class_indices 

if result[0][0] == 1:
    prediction = 'Dog'
else:
    prediction = 'Cat'
    
print("Input Image contains a", prediction)
```

<br/>
<hr/>
<br/>

# Dimensionality Reduction
Working with complex dataset and high dimension dataset is very tedius, there are some techniques that can be used to reduce the dimension, hence decrease the complexity.

## Principal Component Analysis (PCA)
It is an unsupervsed learning dimension reduction algorithm.

**Reduce the dimensions of a d-dimension dataset by projecting it on a k-dimensional subspace, where k < d.** 

Steps of PCA

1. Standardize the data.
2. Obtain the eignvectors and eignvalues from the covariance matrix or correlation matrix, or perform Singular Vector Decomposition.
3. Sort the eignvalues in descending order and choose the k eignvectors that corresponds to the k largest eignvalues, where k is the number of dimensions of the new feature subspace ( k < d )
4. Construct the projection matrix W from the selected k eignvectors.
5. Transform the original dataset X via W to obtain a k dimensional feature subspace X_new. 

Usages of PCA
- Noise Filtering
- Visualization
- Feature Extraction
- Stock Market Prediction
- Gene Data Analysis


Goals of PCA
- Identify patterns in data
- Detect the correlation between variables

### Importing the Libraries and Dataset
```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

dataset = pd.read_csv("./Datasets/Wine.csv")
X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)
```

### Splitting dataset into train and test set
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling
```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Applying PCA
```python
from sklearn.decomposition import PCA
pca = PCA(n_components = 2)
X_train = pca.fit_transform(X_train)
X_test = pca.transform(X_test)
```

### Training the Logistic Regression Model using Training 
```python
from sklearn.linear_model import LogisticRegression
classifier = LogisticRegression(random_state = 0)
classifier.fit(X_train,y_train)
```

### Predict Test results
```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix
```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Customer-0,   Customer-1, Customer-2] => [Correct,Incorrect,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Correct,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Incorrect,Correct]
# ]
```

### Visualising the Training set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_train, y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Training set)')
plt.xlabel('PC1')
plt.ylabel('PC2')
plt.legend()
plt.show()
```

### Visualising the Test set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_test, y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Test set)')
plt.xlabel('PC1')
plt.ylabel('PC2')
plt.legend()
plt.show()
```

## Linear Discriminant Analysis [ LDA ]
It is a supervsed learning dimension reduction algorithm as it's relation to the dependent variable.

**Reduce the dimensions of a d-dimension dataset by projecting it on a k-dimensional subspace, where k < d  and also maintaining the class-discriminatory information.** 

Usages

- Used as a dimensionality reduction technique
- Used in preprocessing step for pattern classification
- Has a goal to project a dataset onto a lower dimension space

LDA is different than PCA, because in addition to finding the component axes with LDA, we are also intrested in the axes that maximize the seperation between multiple classes.

Steps for LDA

1. Compute the d-dimensional mean vectors for the different classes from the dataset.
2. Compute the scatter matrices (in-between-class and within-class scatter matrix).
3. Compute the eignvectors ( e<sub>1</sub> e<sub>2</sub> ..., e<sub>n</sub> ) and corresponding eignvalues ( &Lambda;<sub>1</sub> &Lambda;<sub>2</sub> ..., &Lambda;<sub>n</sub> ) for the scatter matrices.
4. Sort the eignvectors by decreasing eignvalues and choose k eignvectors with the largest eignvalues to form a d*k dimensional matrix W (where every column represtents an eignvector).
5. Use the d*k eignvector matrix to transform the samples onto the new subspace. This can be summarized by the matrix multiplication: Y = X*Y (where X is a n*d  dimensional matrix representing the n samples, and y are the transformed n*k dimensional samples in the new subspace).



### PCA vs LDA
<img src="./Dimensionality_Reduction/PCA_vs_LDA.png">


### Importing the Libraries and Dataset
```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

dataset = pd.read_csv("./Datasets/Wine.csv")
X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)
```

### Splitting dataset into train and test set
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling
```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Applying LDA
```python
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis as LDA
lda = LDA(n_components = 2)
X_train = lda.fit_transform(X_train, y_train)
X_test = lda.transform(X_test)
```

### Training the Logistic Regression Model using Training 
```python
from sklearn.linear_model import LogisticRegression
classifier = LogisticRegression(random_state = 0)
classifier.fit(X_train,y_train)
```

### Predict Test results
```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix
```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Customer-0,   Customer-1, Customer-2] => [Correct,Incorrect,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Correct,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Incorrect,Correct]
# ]
```

### Visualising the Training set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_train, y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Training set)')
plt.xlabel('LD1')
plt.ylabel('LD2')
plt.legend()
plt.show()
```

### Visualising the Test set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_test, y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Test set)')
plt.xlabel('LD1')
plt.ylabel('LD2')
plt.legend()
plt.show()
```

## Kernel PCA (KPCA)

### Importing the Libraries and Dataset
```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

dataset = pd.read_csv("./Datasets/Wine.csv")
X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values

print(X)
print(y)
```

### Splitting dataset into train and test set
```python
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```

### Feature Scaling
```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Applying KPCA
```python
from sklearn.decomposition import KernelPCA
kpca = KernelPCA(n_components = 2, kernel = 'rbf')
X_train = kpca.fit_transform(X_train)
X_test = kpca.transform(X_test)
```

### Training the Logistic Regression Model using Training 
```python
from sklearn.linear_model import LogisticRegression
classifier = LogisticRegression(random_state = 0)
classifier.fit(X_train,y_train)
```

### Predict Test results
```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix
```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Customer-0,   Customer-1, Customer-2] => [Correct,Incorrect,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Correct,Incorrect]
#     [Customer-0,   Customer-1, Customer-2] => [Incorrect,Incorrect,Correct]
# ]
```

### Visualising the Training set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_train, y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Training set)')
plt.xlabel('KPC1')
plt.ylabel('KPC2')
plt.legend()
plt.show()
```

### Visualising the Test set results
```python
from matplotlib.colors import ListedColormap
X_set, y_set = X_test, y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 1, stop = X_set[:, 0].max() + 1, step = 0.01),
                     np.arange(start = X_set[:, 1].min() - 1, stop = X_set[:, 1].max() + 1, step = 0.01))
plt.contourf(X1, X2, classifier.predict(np.array([X1.ravel(), X2.ravel()]).T).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green', 'blue')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1],
                c = ListedColormap(('red', 'green', 'blue'))(i), label = j)
plt.title('Logistic Regression (Test set)')
plt.xlabel('KPC1')
plt.ylabel('KPC2')
plt.legend()
plt.show()
```

<br/>
<hr/>
<br/>

# Model Selection

## K-Fold Cross Validation

### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Kernel_SVM/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Kernel SVM Model using Training Data

```python
from sklearn.svm import SVC
classifier = SVC(kernel = 'rbf', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Applying K-Fold Cross Validation
```python
from sklearn.model_selection import cross_val_score

accuracies = cross_val_score(
    estimator=classifier,
    X=X_train,
    y=y_train,
    cv=10
)

print("Accuracy : {:.2f} %".format(accuracies.mean()*100))

print("Standard Deviation : {:.2f} %".format(accuracies.std()*100))
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

## Grid Search

### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Kernel_SVM/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)

# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the Kernel SVM Model using Training Data

```python
from sklearn.svm import SVC
classifier = SVC(kernel = 'rbf', random_state = 0)
classifier.fit(X_train,y_train)
```

### Predicting a test resullt

```python
# predict a single test 
classifier.predict(sc.transform([[30,87000]]))
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Applying K-Fold Cross Validation
```python
from sklearn.model_selection import cross_val_score

accuracies = cross_val_score(
    estimator=classifier,
    X=X_train,
    y=y_train,
    cv=10
)

print("Accuracy : {:.2f} %".format(accuracies.mean()*100))

print("Standard Deviation : {:.2f} %".format(accuracies.std()*100))
```

### Applying Grid Search to find the best model and the best parameter
```python
from sklearn.model_selection import GridSearchCV

parameters = [
    {
        'C':[0.25, 0.5, 0.75, 1],
        'kernel': ['linear']
        },
    {
        'C':[0.25, 0.5, 0.75, 1],
        'kernel': ['rbf'],
        'gamma': [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
        },
]

grid_search = GridSearchCV(
    estimator=classifier,
    param_grid=parameters,
    scoring='accuracy',
    cv=10,
    n_jobs=-1
)

grid_search.fit(X_train, y_train)

best_accuracy = grid_search.best_score_

best_parameters = grid_search.best_params_

print("Best Accuracy : {:.2f} %".format(best_accuracy*100))

print("Best Parameters :",best_parameters)
```

### Visualising the Training set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_train), y_train
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Training set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```

### Visualising the Test set results

```python
from matplotlib.colors import ListedColormap
X_set, y_set = sc.inverse_transform(X_test), y_test
X1, X2 = np.meshgrid(np.arange(start = X_set[:, 0].min() - 10, stop = X_set[:, 0].max() + 10, step = 5),
                     np.arange(start = X_set[:, 1].min() - 1000, stop = X_set[:, 1].max() + 1000, step = 5))
plt.contourf(X1, X2, classifier.predict(sc.transform(np.array([X1.ravel(), X2.ravel()]).T)).reshape(X1.shape),
             alpha = 0.75, cmap = ListedColormap(('red', 'green')))
plt.xlim(X1.min(), X1.max())
plt.ylim(X2.min(), X2.max())
for i, j in enumerate(np.unique(y_set)):
    plt.scatter(X_set[y_set == j, 0], X_set[y_set == j, 1], c = ListedColormap(('red', 'green'))(i), label = j)
plt.title('Kernel SVM (Test set)')
plt.xlabel('Age')
plt.ylabel('Estimated Salary')
plt.legend()
plt.show()
```


# XGBoost Model


### Loading and Preprocession Data

```python
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

dataset = pd.read_csv('../Datasets/Classification/Kernel_SVM/Social_Network_Ads.csv')
# print(dataset)

X = dataset.iloc[:,:-1].values
y = dataset.iloc[:,-1].values


# # Taking care of Missing values
# from sklearn.impute import SimpleImputer 
# imputer = SimpleImputer(missing_values=np.nan, strategy='mean')
# imputer.fit(X[:,:-1])
# X[:,:-1] =  imputer.transform(X[:,:-1])
# imputer = SimpleImputer(missing_values=np.nan, strategy='most_frequent')
# imputer.fit(X[:,-2:-1])
# X[:,-2:-1] =  imputer.transform(X[:,-2:-1])
# # print(X)

# # Encoding categorial Data [One Hot Encoding]
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# ct = ColumnTransformer(transformers=[('encode',OneHotEncoder(),[-1])], remainder='passthrough')
# X = np.array(ct.fit_transform(X))
# # print(X)


# LabelEncoder for y
from sklearn.preprocessing import LabelEncoder
le = LabelEncoder()
y = le.fit_transform(y)
print(y)


# Splitting dataset into train and test set
from sklearn.model_selection import train_test_split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=0)
print(X_train)
print(y_train)
print(X_test)
print(y_test)
```


### Feature Scaling

```python
from sklearn.preprocessing import StandardScaler
sc = StandardScaler()
# fit using training data
sc.fit(X_train)
# transform training data using the scaler
X_train = sc.transform(X_train)
# transform test data using the same scaler
X_test = sc.transform(X_test)
```


### Training the XGBoost Model using Training Data

```python
from xgboost import XGBClassifier
classifier = XGBClassifier()
classifier.fit(X_train,y_train)
```

### Predict Test results

```python
y_pred = classifier.predict(X_test)
print(np.concatenate((y_pred.reshape(len(y_pred),1), y_test.reshape(len(y_test),1)),axis=1))
```

### Making the Confusion Matrix

```python
from sklearn.metrics import confusion_matrix, accuracy_score
cm = confusion_matrix(y_test,y_pred)
print(cm)
acs = accuracy_score(y_test,y_pred)
print(acs)
# Confusion Matrix
# [
#     [Correct-0,   Incorrect-1]
#     [Incorrect-0, Correct-0]
# ]
```

### Applying K-Fold Cross Validation
```python
from sklearn.model_selection import cross_val_score

accuracies = cross_val_score(
    estimator=classifier,
    X=X_train,
    y=y_train,
    cv=10
)

print("Accuracy : {:.2f} %".format(accuracies.mean()*100))

print("Standard Deviation : {:.2f} %".format(accuracies.std()*100))
```
