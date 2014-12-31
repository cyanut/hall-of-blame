var waiting_for_update = false, 
    LONG_POLL_DURATION = 5000,
    last_board_num = 0,
    results = {},
    boards = []; 
    
    
var request_success = false;

/*
function wait_for_update() {

    if (!waiting_for_update) {
        waiting_for_update = true;
        $.ajax({ url: '/poll',
                 type: 'POST',
                 data: {'boards':JSON.stringify(boards)}
        }).done(function(msg){
                display_data(msg); 
                request_success = true;
                waiting_for_update = false;
                setTimeout(wait_for_update, 500);
        }).fail(function(msg){
                request_success = false;
                waiting_for_update = false;
                setTimeout(wait_for_update, 5000);
        });
    }
}
*/

function display_data(data_raw) {
    var i;
    var data = JSON.parse(data_raw);
    var exists;
    if ($.inArray(data.board_num, boards) === -1){
        if (data.type === "this_table"){
            boards.push(data.board_num);
            $('div#contents').append(data.content);
            if (data.board_num in results){
                display_data(results[data.board_num]);
                delete results[data.board_num];
            }

        } else if (data.type === "other_tables"){
            //queue stand alone result, waiting for table to come
            results[data.board_num] = data;
            return;
        }
       
    } else {
        objs = $(data.content);
        for (var i=0; i<objs.length; i++){
            if (objs[i].nodeType != 1) continue;
            
            if (objs[i].tagName.toLowerCase() == 'script'){
                //run additional scripts
                eval(objs[i].text);
            } else {
                //update elements
                target = $('#'+objs[i].id);
                if (target.length > 0){
                    target = target[0];
                    target.outerHTML = objs[i].outerHTML;
                }
            }
        }
    }
        
        //$("#updated").fadeIn('fast');
        //setTimeout(function() {  $("#updated").fadeOut('slow');  }, 2500);
}

