$(function () {
    jQuery.validator.addMethod("unique", function(value, element, param) {
            return this.optional(element) || $.inArray(value, param) < 0; // <-- Check if the value is not in the array.
        }, "ID is not unique.");
    // TODO: weak agent type associations, prone to id errors
    var $agentForm = $('#agentForm');
    $agentForm.validate(
        {
            rules: {
                nick: {
                    required: true,
                    maxlength: 32,
                    unique: window.nickArray
                }
            },
            highlight: function (label) {
                $(label).closest('.control-group').addClass('error');
            }

        });
    var $divIdIsCreateUser = $("#div_id_is_create_user");
    // $divIdIsCreateUser.hide();

    var $divIdUserEmail = $("#div_id_user_email");
    $divIdUserEmail.hide();

    var $idIsCreateUser = $("#id_is_create_user");
    $idIsCreateUser.on('change', function () {
        $divIdUserEmail.toggle();
    });
    var $idAgentType = $("#id_agent_type");
    var handleSelectChange = function () {
        var val = $idAgentType.find("option:selected").attr("value");
        if (("" + val) == "1") {
            $divIdIsCreateUser.show();
        }
    };
    $idAgentType.on('change', handleSelectChange);
});