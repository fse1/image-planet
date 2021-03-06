
// wait until the base HTML is loaded
document.addEventListener('DOMContentLoaded', function () {
    
    // get needed elements
    const recentContainer = document.querySelector('div.recent-image-container');
    
    // create socket
    let socket = io();

    // handle new images. append to top of recent images
    socket.on('new-image-full', function (data) { 
    
      // handle the no image case
      const noImage = document.querySelectorAll('.recent-image-container p.no-recent-images');
      if (noImage.length > 0) {
        noImage[0].outerHTML = data.html;
      }
      else
      {
        let newImageContainer = document.createElement("div");
        recentContainer.insertBefore(newImageContainer, recentContainer.childNodes[3]);
        newImageContainer.outerHTML = data.html;
      }
      
      // now set up the AJAX handlers
      const likeBtn = document.querySelector('#user-' + data.userid + '-img-' + data.imageid + ' button.like-btn');
      const commentSubmit = document.querySelector('#user-' + data.userid + '-img-' + data.imageid + ' input.submit-comment-btn');
      likeBtn.onclick = likeClick;
      commentSubmit.onclick = comClick;
      
    });
    
    // handle new comments. append to bottom of comment container
    socket.on('new-comment-full', function (data) { 
    
      // try to find the appropriate comment div
      commentContainerCSSID = '#com-block-' + data.imageid;
      const commentContainers = document.querySelectorAll(commentContainerCSSID);
      
      for (commentContainer of commentContainers)
      {
        // check if there are no comments and handle appropriately
        const commentBlocks = document.querySelectorAll(commentContainerCSSID + ' p.no-com')
        if (commentBlocks.length === 0) {
          let newCommentBlock = document.createElement("div");
          commentContainer.appendChild(newCommentBlock);
          newCommentBlock.outerHTML = data.html;
        }
        else
        {
          commentContainer.innerHTML = data.html;
        }
      }
        
    });
    
    // handle new likes. increment the appropriate like count
    socket.on('new-like', function (data) { 
    
      // try to find the appropriate like button
      const likeBtns = document.querySelectorAll('#like-' + data.imageid);
      
      for (likeBtn of likeBtns)
      {
        let likeText = likeBtn.innerHTML;
        let firstParen = likeText.lastIndexOf('(');
        let secondParen = likeText.lastIndexOf(')');
        let likeCount = parseInt(likeText.slice(firstParen + 1, secondParen));
        likeBtn.innerHTML = 'Like This Image! (' + ((likeCount + 1).toString()) + ')';
      }
        
    });
    
    // handle new messages. change the style of the header
    socket.on('new-dm', newNotificationDM);
    
});
