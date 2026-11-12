# Algorithm_learnings

## String Comparision
- If we normally compare strings, it will take `O(mn)`, to avoid extra comparision we can use <b>KMP Algorithm</b>

```python
def prefix_array(s):
  l = len(s)
  pr = [0 for _ in range(l)]
  j =0
  for i in range(1,l):
    while j>0 and s[i] != s[j]:
      j = pr[j-1]

    if s[i] == s[j]:
      j = j + 1
    pr[i] = j
  return pr

def KMP(S, s):
  match = []
  pr = prefix_array(s)
  l, L, j = len(s), len(S), 0
  for i in range(len(S)):
    while j>0 and S[i] != s[j]:
      j = pr[j-1]
    if S[i] == s[j]:
      j+=1
    if j == l:
      match.append(i-l+1)
      j = pr[j-1]
  return match

text = "ABABDABACDABABCABAB"
pattern = "ABABCABAB"
matches = KMP(text, pattern)
print(matches)
```
