
// 配置mathjax
window.MathJax = {};

// 在navigation.instant模式下支持mathjax
document$.subscribe(() => { 
    MathJax.startup.output.clearCache();
    MathJax.typesetClear();
    MathJax.texReset();
    MathJax.typesetPromise();
})

