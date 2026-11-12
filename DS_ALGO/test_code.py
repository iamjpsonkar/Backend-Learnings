def merge(ar,low,mid,high):
    left=ar[low:mid+1]
    right=ar[mid+1:high+1]
    k=low
    i=j=0
    while i<len(left) and j<len(right):
        if left[i]<right[j]:
            ar[k]=left[i]
            i+=1
        else:
            ar[k]=right[j]
            j+=1
        k+=1
    
    while i<len(left):
        ar[k]=left[i]
        i+=1
        k+=1
    
    while j<len(right):
        ar[k]=right[j]
        j+=1
        k+=1

def mergeSort(ar,low, high):
    if low<high:
        mid=(low+high)//2
        mergeSort(ar,low,mid)
        mergeSort(ar,mid+1,high)
        merge(ar,low,mid,high)



import random
n = random.randrange(10,15)
ar = [random.randrange(10, 100) for _ in range(n)]
print(f"List before sorting {ar}")
mergeSort(ar,0,n-1)
print(f"List after sorting {ar}")