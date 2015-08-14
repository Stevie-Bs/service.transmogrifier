var auth_key = '0c9d3e4b3b76e5793f7ca4fdc5725c08'
var auth_pin = '5867'
var base_url = '/api.json'
var __queue_poll__ = false;
var __id__ = false;
$(document).ready(function() {
	var __queue_poll__ = false;
	$("#LoginButton").live("click", function(event, ui) {
		$( "#popupLogin" ).popup( "close" );
		auth_pin=$("#auth_pin").val()
	});
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

	$("#downloadTVFile").live("click", function(event, ui) {
		url = "/query/?method=downloadFile&media=tvshow&file=" + __file__
		window.location.href=url
	});

	var http_call = function(method) {
		base_url = '/api.json'
		request = request = {"method": method, "auth_key": auth_key, "pin": auth_pin}
		notify('b')	
	}
});

function notify(text) {
	$("#notes").html(text);
}
$(document).delegate('#home', 'pageshow', function () {
	__queue_poll__ = false;
});
__file__ = ''
$(document).delegate('#tvshows', 'pageshow', function () {
	__queue_poll__ = false;
	$(".tvshowListItem").live("click", function(event, ui) {
		//url = "/query/?method=downloadFile&media=tvshow&file=" + encodeURIComponent(this.value)
		//window.location.href=url
		__file__ = this.value
	});
	data = JSON.stringify({"method": "tvshows", "auth_key": auth_key, "pin": auth_pin})
	$.post(base_url, data, function(json) {
		html = ''
		$.each(json['tvshows'], function(index){
			row = json['tvshows'][index]
			el = '<li class="tvshowListItem" value="' + encodeURIComponent(row) + '">'
			el += '<a href="#downloadTVFile">'
			el += row
			el += '</a></li>'
			html += el
			
		});
		$('#tvshowList').html(html);
		$('#tvshowList').listview("refresh");
	});
});


$(document).delegate('#movies', 'pageshow', function () {
	__queue_poll__ = false;
	data = JSON.stringify({"method": "movies", "auth_key": auth_key, "pin": auth_pin})
	$.post(base_url, data, function(json) {
		html = ''
		$.each(json['movies'], function(index){
			row = json['movies'][index]
			el = '<li class="movieListItem" value="' + row + '">' + row
			el += '</li>'
			html += el
			
		});
		$('#movieList').html(html);
		$('#movieList').listview("refresh");
	});

});

$(document).delegate('#queue', 'pageshow', function () {
	__queue_poll__ = true;
	$(".queueListItem").live("click", function(event, ui) {
		__id__ = this.value
	});
	data = JSON.stringify({"method": "queue", "auth_key": auth_key, "pin": auth_pin})
	$.post(base_url, data, function(json) {
		html = ''
		$.each(json['queue'], function(index){
			row = json['queue'][index]
			el = '<li class="queueListItem" value="'
			el +=row[0]+'">'
			el += '<a href="#queueContext" data-rel="popup" data-transition="pop" data-position-to="origin">'
			el += '<img src="/images/' +row[1]+'.png" class="ui-li-icon">'
			el += row[2]
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

	var poll_queue = function() {
		setTimeout(function() {
			if (__queue_poll__==true) {
				data = JSON.stringify({"method": "progress", "auth_key": auth_key, "pin": auth_pin})
				$.post(base_url, data, function(json) {
					$('#queue_progress_' + json['progress']['id']).css("width", json['progress']['percent'] +"%");
					if (data.percent == 100) {
						$('#queue_progress_' + json['progress']['id']).css("background", 'blue');
					}
				});
			}
			poll_queue()
		}, 2000);		
		
	}
	poll_queue();
});

$(document).delegate('#log', 'pageshow', function () {
	__queue_poll__ = false;
	$.ajax({
	        type: "GET",
	        url: "/query/?method=getLogContent",
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
