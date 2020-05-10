
// expose necessary function for new message notification
function newNotificationDM (data) {
      
  const msgElement = document.querySelector('header p.header-user-messages');
  const msgElementLink = document.querySelector('header p.header-user-messages a');
  
  if (msgElement && msgElementLink)
  {
    msgElementLink.textContent = 'View New Messages';
    msgElement.className = 'header-user-new-messages';
  }
        
}
