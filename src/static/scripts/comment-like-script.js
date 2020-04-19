
// expose necessary click functions
function likeClick () {
      
  let lbtn = this;
  let data = new FormData(lbtn.parentNode);
  let likeRequest = new XMLHttpRequest(); 
  likeRequest.onreadystatechange = function () { 
    if (this.readyState === 4 && this.status === 200) { 
      lbtn.disabled = true;
    } 
  };
  
  likeRequest.open('POST', '/submit-like');
  likeRequest.send(data);
  return false;
        
}

function comClick () {
      
  let data = new FormData(this.parentNode);
  let comtext = this.previousSibling.previousSibling;
  let ctext = comtext.value.trim();
  
  if (ctext) {
    let comRequest = new XMLHttpRequest(); 
    comRequest.onreadystatechange = function () { 
      if (this.readyState === 4 && this.status === 200) { 
        comtext.value = '';
      } 
    };
    
    comRequest.open('POST', '/submit-comment');
    comRequest.send(data);
  }
  else
  {
    comtext.value = '';
    comtext.focus();
  }
  
  return false;
      
}


// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get necessary elements and add event handlers
    const likeButtons = document.querySelectorAll('button.like-btn');
    const submitCommentButtons = document.querySelectorAll('input.submit-comment-btn');
    
    // set the click event handlers for all like and comment buttons
    for (likebtn of likeButtons)
    {
      likebtn.onclick = likeClick;
    }
    
    for (combtn of submitCommentButtons)
    {
      combtn.onclick = comClick;
    }
    
});
