var global_url = "";

function updateRGB(jscolor) {
    // 'jscolor' instance can be used as a string
    document.getElementById('rect').style.backgroundColor = '#' + jscolor;
    var rgbcolor = hexToRgb('#' + jscolor);
    httpGetAsync2(global_url + "colour/" + rgbcolor.r + "/" + rgbcolor.g + "/" + String(parseInt(rgbcolor.b)));
}

function hexToRgb(hex) {
    var result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return result ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16)
    } : null;
}

function httpGetAsync2(theUrl)
{
    var xmlHttp = new XMLHttpRequest();
    console.log(theUrl);
    xmlHttp.open("GET", theUrl, true); // true for asynchronous
    xmlHttp.send(null);
}