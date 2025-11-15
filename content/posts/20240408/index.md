---
tags:
  - Python
  - tkinter
---

# 关于tkinter接口与引用计数的讨论

> 2024年4月8日，撰写了本文  
> 2025年11月15日，将本文从 `temporary_blogs` 仓库迁移至本仓库

今天在看某个萌新的代码的时候发现了一个问题  
这是一份加载图像并用tkinter显示出来的代码（代码全文会附在最后）  
其中有一个函数“showImg”：
```py
def showImg(img1):
    load = Image.open(img1)
    render = ImageTk.PhotoImage(load)
 
    img = tkinter.Label(image=render)
    img.image = render
    img.pack()
```
我们看到，函数中，`img = tkinter.Label(image=render)`和 `img.image = render` 的语义似乎是重复的。  
于是我们尝试把代码改的更加优雅，一般人的会有如下两种改法：
```py
# 改法一
img = tkinter.Label(image=render)

# 改法二
img = tkinter.Label()
img.image = render
```
然而以上两种改法均会导致程序无法正常运行（图片不显示）
这是怎么回事呢？


代码全文（来自[这篇csdn文章](https://blog.csdn.net/gm_Ergou/article/details/93767575)） ：   
（原文的代码在运行时会报错，但是不影响使用，为了保证原汁原味，此处的代码是完全复制原文的）  

<details markdown="1">
<summary>代码原文</summary>

```py
import tkinter
import tkinter.filedialog
top = tkinter.Tk()
top.title = 'new'
top.geometry('640x480')
 
def choose_fiel():
    selectFileName = tkinter.filedialog.askopenfilename(title='选择文件')  # 选择文件
    e.set(selectFileName)
 
e = tkinter.StringVar()
e_entry = tkinter.Entry(top, width=68, textvariable=e)
e_entry.pack()
 
submit_button = tkinter.Button(top, text ="选择文件", command = choose_fiel)
submit_button.pack()
 
from PIL import Image, ImageTk
def showImg(img1):
    load = Image.open(img1)
    render = ImageTk.PhotoImage(load)
 
    img = tkinter.Label(image=render)
    img.image = render
    img.pack()
 
submit_button = tkinter.Button(top, text ="显示图片", command = lambda :showImg(showImg(e_entry.get())))
submit_button.pack()
top.mainloop()
```
</details>  


<details markdown="1">
<summary>答案（不许偷看哦）</summary>

```py
print(sys.getrefcount(render)) # 2
img = tkinter.Label(image=render)
print(sys.getrefcount(render)) # 2
```
我们发现`render` 的refcount并没有增加。  
于是在函数退出之后，render这个对象就顺理成章地被解释器收走了。  
于是图像就无法正常显示了。  

![](img/320418208-8808f7e1-ad30-4304-8b38-e738dd571b2d.jpg)

</details>
