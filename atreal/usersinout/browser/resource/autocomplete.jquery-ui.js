(function (jq) {
	jq.widget('ui.combobox', jq.ui.autocomplete,
		{
			options: {
        		minLength: 2,
        		ajaxGetAll: { get: 'all' }
			},

        	_create: function () {
        		if (this.element.is('SELECT')) {
        			this._selectInit();
        			return;
        		}

        		jq.ui.autocomplete.prototype._create.call(this);
        		var input = this.element;
        		input.addClass('ui-state-default ui-combobox-input ui-widget ui-widget-content ui-corner-left');
                
        jq( "<a>" )
            .attr('tabIndex', -1)
            .attr('title', 'Exibir todos os itens')
            .insertAfter(input)
            .button({
            	icons: { primary: 'ui-icon-triangle-1-s' },
            	text: false
            })
            .removeClass('ui-corner-all')
            .addClass('ui-corner-right ui-combobox-toggle')
            .click(function (event) {
		if (input.combobox('widget').is(':visible')) {
            		input.combobox('close');
            		return;
            	}
            	var data = input.data('combobox');
            	clearTimeout(data.closing);
            	if (!input.isFullMenu) {
            		data._swapMenu();
            		input.isFullMenu = true;
            	}
            	input.combobox('widget').css('display', 'block')
                .position(jq.extend({ of: input },
                    data.options.position
                    ));
            	input.focus();
            	data._trigger('open');
            });

        		jq(document).queue(function () {
        			var data = input.data('combobox');
        			if (jq.isArray(data.options.source)) {
        				jq.ui.combobox.prototype._renderFullMenu.call(data, data.options.source);
        			} else if (typeof data.options.source === 'string') {
        				jq.getJSON(data.options.source, data.options.ajaxGetAll, function (source) {
        					jq.ui.combobox.prototype._renderFullMenu.call(data, source);
        				});
        			} else {
        				jq.ui.combobox.prototype._renderFullMenu.call(data, data.source());
        			}
        		});
        	},

        	_renderFullMenu: function (source) {
        		var self = this,
                input = this.element,
                ul = input.data('combobox').menu.element,
                lis = [];
        		source = this._normalize(source);
        		input.data('combobox').menuAll = input.data('combobox').menu.element.clone(true).appendTo('body');
        		for (var i = 0; i < source.length; i++) {
        			lis[i] = '<li class="ui-menu-item" role="menuitem"><a class="ui-corner-all" tabindex="-1">' + source[i].label + '</a></li>';
        		}
        		ul.append(lis.join(''));
        		this._resizeMenu();
        		setTimeout(function () {
        			self._setupMenuItem.call(self, ul.children('li'), source);
        		}, 0);
        		input.isFullMenu = true;
        	},

        	_setupMenuItem: function (items, source) {
        		var self = this,
                itemsChunk = items.splice(0, 500),
                sourceChunk = source.splice(0, 500);
        		for (var i = 0; i < itemsChunk.length; i++) {
        			jq(itemsChunk[i])
                .data('item.autocomplete', sourceChunk[i])
                .mouseenter(function (event) {
                	self.menu.activate(event, jq(this));
                })
                .mouseleave(function () {
                	self.menu.deactivate();
                });
        		}
        		if (items.length > 0) {
        			setTimeout(function () {
        				self._setupMenuItem.call(self, items, source);
        			}, 0);
        		} else {
        			jq(document).dequeue();
        		}
        	},

        	_renderItem: function (ul, item) {
        		var label = item.label.replace(new RegExp(
                '(?![^&;]+;)(?!<[^<>]*)(' + jq.ui.autocomplete.escapeRegex(this.term) +
                ')(?![^<>]*>)(?![^&;]+;)', 'gi'), '<strong>$1</strong>');
        		return jq('<li></li>')
                .data('item.autocomplete', item)
                .append('<a>' + label + '</a>')
                .appendTo(ul);
        	},

        	destroy: function () {
        		if (this.element.is('SELECT')) {
        			this.wrapper.remove();
        			this.element.removeData().show();
        			return;
        		}
        		jq.ui.autocomplete.prototype.destroy.call(this);
        		this.element.removeClass('ui-widget ui-widget-content ui-corner-left');
        		this.button.remove();
        	},

        	search: function (value, event) {
        		var input = this.element;
        		if (input.isFullMenu) {
        			this._swapMenu();
        			input.isFullMenu = false;
        		}
        		jq.ui.autocomplete.prototype.search.call(this, value, event);
        	},

        	_change: function (event) {
        		abc = this;
        		if (!this.selectedItem) {
        			var matcher = new RegExp('^' + jq.ui.autocomplete.escapeRegex(this.element.val()) + '$', 'i'),
                    match = jq.grep(this.options.source, function (value) {
                    	return matcher.test(value.label);
                    });
        			if (match.length) {
        				match[0].option.selected = true;
        			} else {
        				this.element.val(this.element.parent().prev().children("option:selected").text());
        				if (this.options.selectElement) {
        					this.options.selectElement.val('');
        				}
        			}
        		}
        		jq.ui.autocomplete.prototype._change.call(this, event);
        	},

        	_swapMenu: function () {
        		var input = this.element,
                data = input.data('combobox'),
                tmp = data.menuAll;
        		data.menuAll = data.menu.element.hide();
        		data.menu.element = tmp;
        	},

        	_selectInit: function () {
        		var select = this.element.hide(),
            selected = select.children(':selected'),
            value = selected.val() ? selected.text() : '';
        		this.options.source = select.children('option[value!=""]').map(function () {
        			return { label: jq.trim(this.text), option: this };
        		}).toArray();
        		var userSelectCallback = this.options.select;
        		var userSelectedCallback = this.options.selected;
        		this.options.select = function (event, ui) {
        			ui.item.option.selected = true;
        			if (userSelectCallback) userSelectCallback(event, ui);
        			if (userSelectedCallback) userSelectedCallback(event, ui);
        		};
        		this.options.selectElement = select;
                wrapper = this.wrapper = jq( "<span>" )
                        .addClass( "ui-combobox" )
                        .insertAfter( select );

        		this.input = jq('<input>').appendTo( wrapper )
                .val(value).combobox(this.options);
        	}
        }
	);
})(jQuery);