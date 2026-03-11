/**
 * NOH Maternity Cost Estimator — WordPress Embed Script
 *
 * Usage: <script src="https://maternity-cost-estimator.onrender.com/static/embed.js"></script>
 *
 * Creates a self-sizing iframe. Works on networkonehealth.co.za and hpmanyonga.com.
 */
(function () {
    var script = document.currentScript;
    var src = script.src.replace('/static/embed.js', '') + '/?embed=true';

    var iframe = document.createElement('iframe');
    iframe.src = src;
    iframe.style.width = '100%';
    iframe.style.border = 'none';
    iframe.style.minHeight = '800px';
    iframe.style.overflow = 'hidden';
    iframe.setAttribute('loading', 'lazy');
    iframe.setAttribute('title', 'NOH Maternity Cost Estimator');

    script.parentNode.insertBefore(iframe, script.nextSibling);

    // Auto-resize on postMessage from the estimator
    window.addEventListener('message', function (e) {
        if (e.data && e.data.type === 'noh-estimator-resize' && e.data.height) {
            iframe.style.height = e.data.height + 'px';
        }
    });
})();
