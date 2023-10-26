function countr(a,b){
    let c=document.getElementById(a).value;
    c = c.split(/\s+/);
    document.getElementById(b).innerHTML=c.length;
    if (c=="")document.getElementById(b).innerHTML=0;
}