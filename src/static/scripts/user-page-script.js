
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get necessary elements and add event handlers
    const followButton = document.querySelector('button.follow-btn');
    
    // set the click event handler
    followButton.onclick = function () {
      let fbtn = this;
      let data = new FormData(fbtn.parentNode);
      let followRequest = new XMLHttpRequest(); 
      followRequest.onreadystatechange = function () { 
        if (this.readyState === 4 && this.status === 200) { 
          fbtn.disabled = true;
          fbtn.textContent = 'Currently Following This User';
        } 
      };
      
      followRequest.open('POST', '/follow');
      followRequest.send(data);
      return false;
    };
    
});
