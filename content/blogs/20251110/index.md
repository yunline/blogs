# Oneliner 分支优化

前情提要：

```py
def a(b):
    if b:
        return c
    return d
```
这样的短路return结构，在一般的代码里看起来很简洁。然而在oneliner中return会带来额外的长度，使代码膨胀成这个样子：
```py
lambda b: [
    (__ol_retv_ztklpqsdxq := None),
    (__ol_ret_qxgcpwwdic := False),
    [(__ol_retv_ztklpqsdxq := c), (__ol_ret_qxgcpwwdic := True)] if b else ...,
    (
        [(__ol_retv_ztklpqsdxq := d), (__ol_ret_qxgcpwwdic := True)]
        if not __ol_ret_qxgcpwwdic
        else ...
    ),
    __ol_retv_ztklpqsdxq,
][-1]
```

## 概念
首先明确一些概念：
- 跳转语句  
  `break`、`continue`和`return`（以及未来说不定会支持的`raise`）这些会导致跳转的语句，统称为“跳转语句”（jump statements）或者“流控语句”（flow-control statements）
- 跳转分支与普通分支  
  以跳转语句结尾的分支，称为“跳转分支”（jump branches），反之，则为“普通分支”（ordinary branches）  
  比如这是一个跳转分支：
  ```py
  ...
      if condition:
          print("hello")
          continue
  ...
  ```
  而这是一个普通分支：
  ```py
  ...
      if condition:
          print("hello")
  ...
  ```

## continue优化？
优化路漫漫，最核心的思路就是变换分支结构，使得辅助变量`__ol_*`出现的次数最少。

### 临时变量？
我们看这样的例子：
```py
if condition:
    # 分支1
    continue
# 分支2
```
在没有优化的情况下，oneliner-py 会把跳转分支之后的所有分支包裹在一个大的分支里，然后用一个临时变量控制跳转：
```py
jump = False
if condition:
    # 分支1
    jump=True
if not jump:
    # 分支2
```

### 移动分支？
引入临时变量显然会导致产物膨胀，我们可以通过改变分支结构来避免跳转，从而避免引入临时变量吗？答案是肯定的  
```py
if condition:
    # 分支1
else:
    # 分支2
```
有小朋友问“主播主播你这个分支结构变换确实厉害，但是如果分支1本来就在else里，该怎么办呢？”  
确实，让我们看这样的情况：
```py
if condition:
    # 分支0
else:
    # 分支1
    continue
# 分支2
```
实际上这也并非不可转换，只需要把分支2移动一下位置：
```py
if condition:
    # 分支0
    # 分支2
else:
    # 分支1
```
但是如果遇到那种有很多elif的情况，这种做法就不管用了：
```py
if condition:
    # 分支0.0
elif condition1:
    # 分支0.1
elif condition2:
    # 分支0.2
...
else:
    # 分支1
    continue
# 分支2
```
显然如果要通过移动分支2解决问题，就需要把分支2复制若干次，不仅没有缩小产物，反而使产物膨胀。
```py
if condition:
    # 分支0.0
    # 分支2
elif condition1:
    # 分支0.1
    # 分支2
elif condition2:
    # 分支0.2
    # 分支2
...
else:
    # 分支1
```
这就是“最坏的情况”，这时候我们就不得不使用临时变量了。  

还有比如分支1在elif里的情况, 其实也不得不借助临时变量：
```py
if condition:
    # 分支0.0
elif condition1:
    # 分支1
    continue
...
else:
   # 分支0.x
# 分支2
```

也不能一概而论，如果所有分支0.i都是跳转分支，只有分支1是普通分支：
```py
if condition0:
    # 分支0.0
    continue
elif condition1:
    # 分支0.1
    continue
elif condition2:
    # 分支0.2
    continue
elif condition:
    # 分支1
    # 注意，这里没有continue
...
else:
   # 分支0.x
   continue
# 分支2
```
那么也是可以优化的：
```py
if condition0:
    # 分支0.0
elif condition1:
    # 分支0.1
elif condition2:
    # 分支0.2
elif condition:
    # 分支1
    # 分支2
...
else:
   # 分支0.x
```
从另一个角度来看，continue本质上是一条去往循环末尾的路径。
如果能通过变换，把continue移动到循环的末尾，也就成功地消除了continue。

### 最坏的情况？
对于这样的情形：
```py
if condition1:
    # 分支1
elif condition2:
    # 分支2
    continue
elif condition3:
    # 分支3
elif condition4:
    # 分支4
elif condition5:
    # 分支5
# 分支6
```
似乎是“最坏的情况”，但真的是这样吗？  
```py
if condition1:
    # 分支1
    # 分支6
elif condition2:
    # 分支2
else:
    if condition3:
        # 分支3
    elif condition4:
        # 分支4
    elif condition5:
        # 分支5
    # 分支6
```
你看，虽然4个“非continue分支”，但是我们只复制了2份分支6。


