$(document).ready(function() {
	var __queue_poll__ = false;

	$("#queueRestart").live("click", function(event, ui) {
		$('#queue_progress_' + __id__).css("width", "0%")
		$('#queue_progress_' + __id__).css("background", 'green');
		$.getJSON('/query/?method=restartQueue&id=' + __id__);	
		$( "#queueContext" ).popup( "close" );
	});

	$("#queueAbort").live("click", function(event, ui) {
		$('#queue_progress_' + __id__).css("background", 'red');
		$.getJSON('/query/?method=abortQueue&id=' + __id__);	
		$( "#queueContext" ).popup( "close" );
	});

	$("#queueDelete").live("click", function(event, ui) {
		$.getJSON('/query/?method=deleteQueue&id=' + __id__);
		$( "#queueContext" ).popup( "close" );
	});
});

function notify(text) {
	$("#notes").html(text);
}


$(document).delegate('#tvshows', 'pageshow', function () {
	$.getJSON('/query/?method=getTVShows', function(json) {
		html = ''
		$.each(json, function(index){
			row = json[index]
			el = '<li class="tvshowListItem" value="' + row + '">' + row
			el += '</li>'
			html += el
			
		});
		$('#tvshowList').html(html);
		$('#tvshowList').listview("refresh");
	});
});


$(document).delegate('#movies', 'pageshow', function () {
	$.getJSON('/query/?method=getMovies', function(json) {
		html = ''
		$.each(json, function(index){
			row = json[index]
			el = '<li class="movieListItem" value="' + row + '">' + row
			el += '</li>'
			html += el
			
		});
		$('#movieList').html(html);
		$('#movieList').listview("refresh");
	});

});
var __queue_poll__ = false;
var __id__ = false;
$(document).delegate('#queue', 'pageshow', function () {
	$(".queueListItem").live("click", function(event, ui) {
		__id__ = this.value
	});

	$.getJSON('/query/?method=getQueue', function(json) {
		html = ''
		$.each(json, function(index){
			row = json[index]
			html += '<li class="queueListItem" value="'+row[0]+'"><a href="#queueContext" data-rel="popup" data-transition="pop" data-position-to="origin">'+row[1]+' - '+row[2]+'</a><div class="queueprogress" id="queue_progress_'+row[0]+'"></div></li>'
		});
		$('#queueList').html(html);
		$('#queueList').listview("refresh");
		$.each(json, function(index){
			row = json[index]
			if (row[3] == 3) {
				$('#queue_progress_' + row[0]).css("width", "100%")
				$('#queue_progress_' + row[0]).css("background", 'blue');			
			} else if(row[3] == 0 || row[3] == 2){
				$('#queue_progress_' + row[0]).css("width", "100%")
				$('#queue_progress_' + row[0]).css("background", 'red');
			} else {
				$('#queue_progress_' + row[0]).css("width", "0%")
				$('#queue_progress_' + row[0]).css("background", 'green');
			}
		});	
	});
	__queue_poll__ = true;
	var poll_queue = function() {
		setTimeout(function() {
			if (__queue_poll__==true) {
				$.getJSON( "/query/?method=getProgress", function( data ) {
					$('#queue_progress_' + data.id).css("width", data.percent +"%");
					if (data.percent == 100) {
						$('#queue_progress_' + data.id).css("background", 'blue');
					}
				});
			}
			poll_queue()
		}, 2000);		
		
	}
	poll_queue();
});

$(document).delegate('#queue', 'pageremove', function () {
	//$('#queue_progress_2').css("width", "0");
	__queue_poll__ = false;
});

$(document).delegate('#log', 'pageshow', function () {
	$.ajax({
	        type: "GET",
	        url: "/query/?method=getLogContent",
	        cache: false,
	        success: function(response) {
			$('#logcontent').html('<pre>' + response + '</pre>');
		}
	});
	

});
