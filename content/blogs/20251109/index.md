# Oneliner-Py 结构解析pass

这个pass解析一些结构相关的信息

## 例1：跳转结构

比如你有这样的一个循环

```py
a = 0
while True:
    a+=1
    if a==5:
        break
    print(a)

```
但是显然你不可能在oneliner里直接使用break语句的。  
所以我们定义了一个__ol_break临时变量。在需要break时将其设为True。  
然后在进入break之后的任何一个分支时，进行额外的检查。如果break已经发生，则这个分支不执行，跳转到循环尾部结束循环。就像这样：
```py
a = 0
__ol_break = False
while True and not __ol_break:
    a+=1
    if a==5:
        __ol_break = True
    if not __ol_break:
        print(a)
```

对于层叠的循环，在Oneliner-Py 1.2，我们写了一个“循环栈”，用于存储break/continue相关的上下文，根据这个上下文信息来生成分支。具体处理分支则是在`_iter_branch`。写的很晦涩，耦合很严重，不好单元测试。

现在我们把这个分析与generate pass拆开来。在结构解析pass中，我们建立循环树，该树每个节点对应当前scope里的一个循环。把分支按照break/continue/return切分好，存储在节点里待生成pass取用。  

## 例2：注入__class__

当你使用没有带参数的`super()`时，实际上等价于`super(定义当前函数的类, 当前函数的第一个参数)`。读函数的参数固然容易，只需要对frame进行一些黑魔法就可以了。然而如何知道函数是在哪个类里定义的呢？

cpython给出的解决办法是在编译字节码时，往这个函数的命名空间里注入一个名为`__class__`的闭包变量。这个闭包变量指向的正是“定义当前函数的类”。至少对于cpython而言，无参数`super()`完全依赖这个隐式的`__class__`工作。

虽然这个闭包变量好像有点脆弱，比如你如果对`__class__`赋值，则会把它立即变成local变量，导致super无法正常工作，就像这样。

```py
class B:
    def meth(self):
        print("hello")

class A(B):
    def meth(self):
        super().meth()
        __class__ = 0

A().meth()

# 报错 RuntimeError: super(): __class__ cell not found
```

不过这和我们聊的主题没什么关系，这里暂且略过。

显而易见的是，oneliner不可能构造一个标准的class scope，从而不可能借助cpython的机制注入`__class__`。为了让super正常工作，我们需要手动注入一个`__class__`闭包变量。
就像这样：

```py
# 转换之前
class A(B):
    def meth(self):
        super().meth()

# 转换之后
[
    (A := type("A", (B,), {})),
    (
        __ol_loader_kszruhmawi := (
            lambda: [
                (__class__ := A), # 显式地注入 __class__
                (__ol_classnsp_rduzgvmcrg := {}),
                __ol_classnsp_rduzgvmcrg.__setitem__(
                    "meth",
                    lambda self: [
                        (__ol_retv_eshpbzsmsn := None),
                        super().meth(),
                        __ol_retv_eshpbzsmsn,
                    ][-1],
                ),
                __ol_classnsp_rduzgvmcrg,
            ][-1]
        )
    ),
    [setattr(A, k, v) for k, v in __ol_loader_kszruhmawi().items()],
]
```
在Oneliner-Py 1.2，分析函数里是否包含无参super，这个步骤是由Namespace生成时进行的，实际上依赖于标准库的symtable。因为这个隐式注入的变量能在标准库的symtable里看到。  
然而由于symtable和解释器底层耦合太强，抽象程度不够。几乎每次cpython大版本更新都会导致兼容性问题，这次重构，我们自己写一个抽象的作用域分析器。  
这个作用域分析器显然是不可能像symtable一样往命名空间里夹带私货的。因此这些私货就需要在结构分析pass里处理了。

## 例3：简化结构

```py
def a(b):
    if b:
        return c
    return d
```
这样的短路return结构，在一般的代码里看起来很简洁。然而在oneliner中return会带来额外的长度，使代码变成这个样子：
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
实际上这样的代码可以优化成：
```py
lambda b: [
    (__ol_retv_ztklpqsdxq := c) if b else (__ol_retv_ztklpqsdxq := d)
    __ol_retv_ztklpqsdxq,
][-1]
```
或者更激进一点
```py
lambda b: c if b else d
```
但是具体怎么实现，我还没想好。
