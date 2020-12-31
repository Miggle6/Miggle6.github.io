function SetContent(content) {
    console.log("SetContent("+content+")");
    //Make all fields invisible
    var elem=document.querySelectorAll('#tab-content div');
    console.log("elem.length:"+elem.length);
    for(var i=0; i<elem.length; ++i) {
        elem[i].classList.add("fade");
        elem[i].classList.add("hidden");
        elem[i].classList.remove("active");
    }
    elem=document.querySelectorAll('.header-info');
    for(var i=0; i<elem.length; ++i) {
        elem[i].classList.add("hidden");
    }
    //Make fields visible for the selected content
    if(content=='Summary') {
        elem=document.querySelectorAll('.header-info');
        for(var i=0; i<elem.length; ++i) {
            elem[i].classList.remove("hidden");
        }
        elem=document.querySelector('#Summary');
    } else if(content=='Page1') {
        elem=document.querySelector('#Page1');
    } else if(content=='Page2') {
        elem=document.querySelector('#Page2');
    } else if(content=='Page3') {
        elem=document.querySelector('#Page3');
    } else if(content=='Page4') {
        elem=document.querySelector('#Page4');
    } else if(content=='Page5') {
        elem=document.querySelector('#Page5');
    } else if(content=='Page6') {
        elem=document.querySelector('#Page6');
    } else if(content=='Page7') {
        elem=document.querySelector('#Page7');
    } else if(content=='Page8') {
        elem=document.querySelector('#Page8');
    } else if(content=='Page9') {
        elem=document.querySelector('#Page9');
    } else if(content=='Page10') {
        elem=document.querySelector('#Page10');
    } else if(content=='Page11') {
        elem=document.querySelector('#Page11');
    } else if(content=='Page12') {
        elem=document.querySelector('#Page12');
    } else if(content=='Page13') {
        elem=document.querySelector('#Page13');
    } else if(content=='Page14') {
        elem=document.querySelector('#Page14');
    } else if(content=='Page15') {
        elem=document.querySelector('#Page15');
    }
if(elem!=undefined) {
        SetActive(elem);
    }
}

function SetActive(elem) {
    elem.classList.remove("hidden");
    elem.classList.remove("fade");
    elem.classList.add("fade-in");
    elem.classList.add("active");
}
