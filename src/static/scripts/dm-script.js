
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get necessary elements and add event handlers
    const dmButton = document.querySelector('input.submit-dm-btn');
    
    // click function
    function dmClick () {
          
      let data = new FormData(this.parentNode);
      let dmtext = this.previousSibling.previousSibling;
      let dtext = dmtext.value.trim();
      
      if (dtext) {
        let dmRequest = new XMLHttpRequest(); 
        dmRequest.onreadystatechange = function () { 
          if (this.readyState === 4 && this.status === 200) { 
            dmtext.value = '';
            dmtext.focus();
          } 
        };
        
        dmRequest.open('POST', '/submit-dm');
        dmRequest.send(data);
      }
      else
      {
        dmtext.value = '';
        dmtext.focus();
      }
      
      return false;
          
    }
    
    
    // set the click event handlers for the direct message submission button
    dmButton.onclick = dmClick;
    
});
