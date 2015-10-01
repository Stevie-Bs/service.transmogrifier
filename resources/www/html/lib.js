$(document).ready(function() {
	var __queue_poll__ = false;
	$("#LoginButton").live("click", function(event, ui) {
		$( "#popupLogin" ).popup( "close" );
		auth_pin=$("#auth_pin").val()
		data = JSON.stringify({"method": "authorize", "pin": auth_pin})
		$.post(base_url, data, function(json) {
			if (json['status'] == 401) {
				alert("Login Error.\nInvalid PIN");
			} else {
				token = json['token']
				setCookie("token", token,1)
			}
		});	
	});
	$("#queueRestart").live("click", function(event, ui) {
		$('#queue_progress_' + __id__).css("width", "0%")
		$('#queue_progress_' + __id__).css("background", 'green');
		data = JSON.stringify({"method": "restart", "token": token, "videos": [{"id":__id__}]})
		$.post(base_url, data);
		$( "#queueContext" ).popup( "close" );
		loadQueuePage();
	});

	$("#queueAbort").live("click", function(event, ui) {
		
		data = JSON.stringify({"method": "abort", "token": token, "id": __id__})
		$.post(base_url, data);
		$( "#queueContext" ).popup( "close" );
		loadQueuePage();
		$('#queue_progress_' + __id__).css("background", 'red');
		$('#queue_progress_detail_' + __id__).text('')
		$('#queue_progress_detail_' + __id__).css('visibility', 'hidden');
	});

	$("#queueDelete").live("click", function(event, ui) {
		data = JSON.stringify({"method": "delete", "token": token, "videos": [{"id":__id__}]})
		$.post(base_url, data);
		$( "#queueContext" ).popup( "close" );
		loadQueuePage();
	});

	$("#EnqueueButtonCacnel").live("click", function(event, ui) {
		$( "#addToQueue" ).popup( "close" );
	});
	$("#EnqueueButton").live("click", function(event, ui) {
		url = $('#queue_url').val()
		filename = $('#queue_filename').val()
		video_type = $("#queue_video_type-1").attr("checked") == 'checked' ? 'tvshow': 'movie';
		resolve = $("#queue_resolve_url").attr("checked") == 'checked' ? "true" : "false";
		data = JSON.stringify({"method": "enqueue", "token": token, "videos": [{"type":video_type, "filename": filename, "resolve": resolve, "raw_url": url, "url": url}]})
		$.post(base_url, data);
		$( "#addToQueue" ).popup( "close" );
		loadQueuePage();
	});
	$( "#addToQueue" ).bind({
		popupafterclose: function(event, ui) { 
			$('#queue_url').val('')
			$('#queue_filename').val('')
			$("input[type='radio']:first").attr("checked", "checked");
			$("input[type='radio']").checkboxradio("refresh");
			$("#queue_resolve_url").attr("checked",false).checkboxradio("refresh");
		}
	});
	
	data = JSON.stringify({"method": "validate_token", "token": token})
	$.post(base_url, data, function(json) {
		if (json['status']==401) {
			$( "#popupLogin" ).popup( "open" );
		}
	});
});



$(document).delegate('#home', 'pageshow', function () {
	__queue_poll__ = false;
});

$(document).delegate('#tvshows', 'pageshow', function () {
	__queue_poll__ = false;
	$(".tvshowListItem").live("click", function(event, ui) {
		__file__ = __files__[this.value]
		url = "/query/download/?media=tvshow&file=" + __file__
		window.location.href=url
	});
	data = JSON.stringify({"method": "tvshows", "token": token})
	$.post(base_url, data, function(json) {
		html = ''
		$.each(json['tvshows'], function(index){
			row = json['tvshows'][index]
			el = '<li class="tvshowListItem" value="' + encodeURIComponent(row) + '">'
			el += '<a href="#downloadTVFile"><img src="images/tvshow.png" class="ui-li-icon">'
			el += row
			el += '</a></li>'
			html += el
			__files__ = json['tvshows']
		});
		$('#tvshowList').html(html);
		$('#tvshowList').listview("refresh");
	});
});


$(document).delegate('#movies', 'pageshow', function () {
	__queue_poll__ = false;
	data = JSON.stringify({"method": "movies", "token": token})
	$.post(base_url, data, function(json) {
		html = ''
		$.each(json['movies'], function(index){
			row = json['movies'][index]
			el = '<li class="movieListItem" value="' + encodeURIComponent(row) + '">'
			el += '<a href="#downloadMovieFile"><img src="images/movie.png" class="ui-li-icon">'
			el += row
			el += '</a></li>'
			el += '</li>'
			html += el
			
		});
		$('#movieList').html(html);
		$('#movieList').listview("refresh");
	});

});

var loadQueuePage = function() {
	__queue_poll__ = true;
	$(".queueListItem").live("click", function(event, ui) {
		__id__ = this.value
	});
	data = JSON.stringify({"method": "queue", "token": token})
	$.post(base_url, data, function(json) {
		html = ''
		__queue_data__ = json['queue']
		$.each(json['queue'], function(index){
			row = json['queue'][index]
			if (row[3] == 2) {
				__fileid__ = row[5]
			}
			el = '<li class="queueListItem" value="'
			el +=row[0]+'">'
			el += '<a href="#queueContext" data-rel="popup" data-transition="pop" data-position-to="origin">'
			el += '<img src="images/' +row[1]+'.png" class="ui-li-icon">'
			el += row[2]
			el += '<span id="queue_progress_detail_'+row[0]+'" class="ui-li-aside" style="font-weight: normal; font-size: 10pt; visibility:hidden;"></span>'
			el += '</a><div class="queueprogress" id="queue_progress_'
			el += row[0]
			el += '"></div></li>'
			html += el
		});
		$('#queueList').html(html);
		$('#queueList').listview("refresh");
		$.each(json['queue'], function(index){
			row = json['queue'][index]
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
	poll_queue();
}
var poll_queue = function() {
	setTimeout(function() {
		if (__queue_poll__==true) {
			data = JSON.stringify({"method": "progress", "token": token, "fileid": __fileid__})
			$.post(base_url, data, function(json) {
				details = "{0} of {1} at {2}KBs in {3}/{4} blocks".format(
					format_size(json['progress']['cached_bytes']), 
					format_size(json['progress']['total_bytes']),
					json['progress']['speed'],
					json['progress']['cached_blocks'],
					json['progress']['total_blocks']
				);
				percent = json['progress']['percent']
				$('#queue_progress_' + json['progress']['id']).css("width", json['progress']['percent'] +"%");
				$('#queue_progress_detail_' + json['progress']['id']).css('visibility', 'visible');
				$('#queue_progress_detail_' + json['progress']['id']).text(details)
				if (percent == 100) {
					$('#queue_progress_' + json['progress']['id']).css("background", 'blue');
					$('#queue_progress_detail_' + json['progress']['id']).text('')
					$('#queue_progress_detail_' + json['progress']['id']).css('visibility', 'hidden');
					loadQueuePage()
				}
			});
			poll_queue();
		}
	}, 2000);
	
}
$(document).delegate('#queue', 'pageshow', loadQueuePage);

$(document).delegate('#log', 'pageshow', function () {
	__queue_poll__ = false;
	$.ajax({
		type: "GET",
		url: "/query/log",
		cache: false,
		success: function(response) {
			$('#logcontent').html('<pre>' + response + '</pre>');
		}
	});
	

});



$(document).delegate('#addTVShow', 'pageshow', function () {
	$("#addTVShowSearchField").live("keyup", function(event, ui) {
		var text = $(this).val();
		if(text.length > 3)	{
			var url = '/query/?method=search&type=tvshows&s=' + encodeURIComponent(text);
			$.getJSON(url , function(json) {
				html = ''
				$.each(json, function(index){
					row = json[index]
					html += '<li><input type="checkbox"  value="'+row[1]+'" class="tvshowAddItem"/>'+row[0]+'</li>';
				}); 
				$('#addTVShowSearchResults').html(html);
				$('#addTVShowSearchResults').listview("refresh");
				$("#addTVShowSearchResults").show('fast');	
			});
					
		} else {
			$("#addTVShowSearchResults").hide('fast');		
		}
		
	});

	/*$(".subscriptionItem").live("change", function(event, ui) {
		
		value = $(this).val();
		data = {"showid" : value};		
		$.ajax({
		        type: "POST",
		        url: "/query/?method=toggleShowSubscription",
		        cache: false,
		        data: data,
		        success: function(response) {
				notify(response);
			}
		});	
	});*/
	
});
