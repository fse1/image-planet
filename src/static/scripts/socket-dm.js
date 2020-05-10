
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
  // get needed elements and values
  const chatContainer = document.querySelector('main div.message-window');
  const userID = parseInt((document.querySelector('main input.user-id')).value);
  const dmID = (document.querySelector('main input.dm-id')).value;
  
  // create socket
  let socket = io();

  // handle new direct messages
  socket.on('new-dm', function (data) { 

    // make sure it is for this direct message
    if (data.dmid === dmID)
    {
      // append the chat message
      let newChatElement = document.createElement("div");
      chatContainer.appendChild(newChatElement);
      newChatElement.outerHTML = data.msghtml;
      
      // send a confirmation back if necessary
      if (data.senduserid !== userID)
      {
        socket.emit('dm-receipt', data.dmid);
      }
    }
    // else, push a notification
    else
    {
      newNotificationDM(data);
    }
    
  });
    
});
