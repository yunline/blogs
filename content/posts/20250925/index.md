---
tags:
  - 嵌入式
  - i2c
  - 状态机
---

# 关于i2c和异步执行的讨论

今天想写点异步的i2c，于是和d老师聊

我：
>   有没有一种轻量化的，可以跑在单片机上的并发系统？
>
>   比如i2c发送数据，在没有dma的机器上，每个字节都需要由cpu自己填入。然而i2c时钟远远慢于cpu时钟，所以cpu需要等待上个字节发送完，然后才能发送下一个字节。我们完全可以利用等待的这一段时间做别的事情。
>
>   如果使用i2c中断，由于中断系统对于硬件依赖较大，导致移植可能比较麻烦。
>
>   所以我想，如果能在等待的时候把cpu交给别的任务，等别的任务用完了再回来看发送完成没有。注意，这不是线程系统，而是类似于协程。如果别的任务不把cpu交回，那么上下文并不会被强制切换。
>
>   我描述的东西，现在有现成的开源项目吗

d老师推荐我使用protothreads，具体内容这里省略。

经过思考，我想这样实现
- i2c_write函数把数据加入环形缓冲区，无需等待i2c传输
- i2c_flush函数把数据从缓冲区搬到i2c外设，这个函数可以用protothreads做成异步的

但是后来一想，真的有必要在发送i2c的时候并发地进行别的工作吗？

定时器的中断发过来，于是显示缓冲区的数据被修改，然后i2c发送启动。在i2c工作的同时，有可能需要同时做的任务有：清零/关机按钮的中断、定时器数值更新的中断。我们发现这些任务全都是中断，本来就是并发执行的，并且不是每时每刻都在执行的。似乎i2c发送的等待，使用轮询除了功耗稍高一点以外，并不会导致什么问题，吗？

## i2c的超时

由于硬件鲁棒性的原因，i2c有时可能会受到干扰，导致收不到ack，从而轮询陷入死循环，系统死机。

如果把超时检测写在每一个i2c收发相关函数的轮询条件里，错误则返回异常值，那么每个调用i2c收发的函数都需要做额外的错误检查，每个调用调用i2c收发的函数的函数，也要做额外的错误检查，子子孙孙无穷匮也。这是不利于抽象和移植的。

但是如果我们把i2c的write和flush拆分开，那么write是无等待的，不可能卡死；在flush里检测i2c传输是否超时，如果超时则重置整个i2c外设，然后重新初始化，重新传输。这样就规避了一些由于i2c传输错误导致的死机。

d老师除了推荐protothreads，还推荐我自己实现一个状态机。
<details>

> ### 3. 状态机 (State Machine) - 最基础的方法
> 
> 在你考虑引入任何库之前，你应该了解，你所描述的模式本质上就是一个**状态机**。你可以手动实现一个轻量的合作式系统。
>
> **示例：使用switch-case的状态机实现I2C发送：**
> ```c
> typedef enum {
>     I2C_STATE_IDLE,
>     I2C_STATE_START,
>     I2C_STATE_SEND_BYTE,
>     I2C_STATE_WAIT_ACK,
>     I2C_STATE_STOP
> } i2c_state_t;
> 
> // 全局状态机变量
> static i2c_state_t i2c_state = I2C_STATE_IDLE;
> static uint8_t *i2c_data_ptr;
> static int i2c_data_count;
> 
> void i2c_send_async(uint8_t *data, int len) {
>     if(i2c_state == I2C_STATE_IDLE) {
>         i2c_data_ptr = data;
>         i2c_data_count = len;
>         i2c_state = I2C_STATE_START;
>     }
> }
> 
> // 这个函数在主循环中被周期性调用
> void i2c_state_machine_update(void) {
>     switch(i2c_state) {
>         case I2C_STATE_IDLE:
>             break;
> 
>         case I2C_STATE_START:
>             i2c_start();
>             i2c_state = I2C_STATE_SEND_BYTE;
>             break;
> 
>         case I2C_STATE_SEND_BYTE:
>             i2c_send_byte(*i2c_data_ptr);
>             i2c_state = I2C_STATE_WAIT_ACK;
>             break;
> 
>         case I2C_STATE_WAIT_ACK:
>             // 检查硬件标志位，如果字节发送完成，就继续
>             if(i2c_byte_sent()) {
>                 i2c_data_ptr++;
>                 i2c_data_count--;
>                 if(i2c_data_count > 0) {
>                     i2c_state = I2C_STATE_SEND_BYTE; // 发送下一个字节
>                 } else {
>                     i2c_state = I2C_STATE_STOP; // 所有字节发送完毕
>                 }
>             }
>             // 如果没发送完，就保持WAIT_ACK状态，下次循环再来检查
>             break;
> 
>         case I2C_STATE_STOP:
>             i2c_stop();
>             i2c_state = I2C_STATE_IDLE;
>             break;
>     }
> }
> 
> // 主循环
> int main() {
>     while(1) {
>         i2c_state_machine_update(); // 非阻塞的I2C任务
>         other_task(); // 执行其他任务
>     }
> }
> ```
>
> 这种方法不需要任何外部库，完全由你自己控制，非常直观和高效。

</details>


考虑到我只需要一个任务，使用并发框架确实有点大材小用的意思。我会尝试一下d老师的建议。
