
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
  // get needed elements and values
  const listContainer = document.querySelector('main ul.dm-list');
  const userID = (document.querySelector('main input.user-id')).value;
  let userid_list = [];
  
  // get dm information
  const emptyElement = document.querySelector('main li.empty-list');
  if (!emptyElement) {
    
    let conversations = document.querySelectorAll('main ul.dm-list li');
    for (conver of conversations)
    {
      userid_list.push(conver.id);
    }
    
  }
  
  // create socket
  let socket = io();

  // handle new direct messages
  socket.on('new-dm', function (data) { 

    // adjust input
    data.senduserid = data.senduserid.toString();
    console.log(data.senduserid);
    console.log(userid_list);
    
    if (data.senduserid !== userID) {
      
      // check if the conversation already exists
      if (userid_list.indexOf('conver-' + data.senduserid) !== -1)
      {
        // modify the current element
        let conversationElem = document.querySelector('main ul.dm-list li#conver-' + data.senduserid);
        if (conversationElem.textContent.indexOf('Unread Messages! -') !== 0) {
          conversationElem.innerHTML = '<span class="error-text">Unread Messages! - </span>' + conversationElem.innerHTML; 
        }          
      }
      else
      {
        // add conversation to list and append element. check for emptiness
        userid_list.push(data.senduserid);
        console.log(userid_list);
        
        if (emptyElement) {
          emptyElement.outerHTML = data.listhtml;
        }
        else
        {
          let newConversationElement = document.createElement("div");
          listContainer.appendChild(newConversationElement);
          newConversationElement.outerHTML = data.listhtml;
        }
      }
      
    }
    
  });
    
});
