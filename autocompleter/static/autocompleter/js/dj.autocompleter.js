(function ($) {
    const autocompleterSelectField = function () {
        const self = $(this);
        const parent = self.parent();
        const dataField = parent.find('input[type=hidden]');

        // set options
        const options = {
            url: self.data('autocompleter-url'),
            databaseField: self.data('autocompleter-db-field'),
            displayNameField: self.data('autocompleter-name-field')
        };

        const removeSearchResults = function () {
            parent.find('ul, li').remove();
        };

        const listItemClick = function (event) {
            const value = $(this).data('value');
            self.val($(this).text());
            dataField.val(value);
            removeSearchResults();
        };

        const autocompleterCallback = function (searchResults) {
            // parse data, put into <li> items
            removeSearchResults();
            const resultsList = $('<ul class="autocompleter-results-list"></ul>');
            if (searchResults.length) {
                searchResults.forEach((searchResult) => {
                    const listItem = $(`<li class="result-item" ` +
                        `data-value="${searchResult[options.databaseField]}">` +
                        `${searchResult[options.displayNameField]}</li>`);
                    listItem.on('click', listItemClick);
                    resultsList.append(listItem);
                });
            } else {
                const query = $(self).val();
                const noResult = $(`<li>There are no results for "${query}"</li>`);
                resultsList.append(noResult);
            }
            parent.append(resultsList);
        };

        const suggest = function () {
            const query = {
                q: $(self).val(),
            };
            $.getJSON(options.url, query, autocompleterCallback);
        };
        self.on('keyup', suggest);
    };

    $.fn.extend({
        bindAutocompleterSelectField: autocompleterSelectField,
    });

    $(document).ready(() => {
        $('input[data-autocompleter]').each(function () {
            $(this).bindAutocompleterSelectField();
        });
    });
}(django.jQuery));
