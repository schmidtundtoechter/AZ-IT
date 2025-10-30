app_name = "az_it"
app_title = "Az It"
app_publisher = "ahmad mohammad"
app_description = "az app"
app_email = "ahmad900mohammad@gmail.com"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "az_it",
# 		"logo": "/assets/az_it/logo.png",
# 		"title": "Az It",
# 		"route": "/az_it",
# 		"has_permission": "az_it.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/az_it/css/az_it.css"
# app_include_js = "/assets/az_it/js/az_it.js"

# include js, css files in header of web template
# web_include_css = "/assets/az_it/css/az_it.css"
# web_include_js = "/assets/az_it/js/az_it.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "az_it/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Lead" : "az_it/js_scripts/lead.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "az_it/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "az_it.utils.jinja_methods",
# 	"filters": "az_it.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "az_it.install.before_install"
# after_install = "az_it.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "az_it.uninstall.before_uninstall"
# after_uninstall = "az_it.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "az_it.utils.before_app_install"
# after_app_install = "az_it.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "az_it.utils.before_app_uninstall"
# after_app_uninstall = "az_it.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "az_it.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"az_it.tasks.all"
# 	],
# 	"daily": [
# 		"az_it.tasks.daily"
# 	],
# 	"hourly": [
# 		"az_it.tasks.hourly"
# 	],
# 	"weekly": [
# 		"az_it.tasks.weekly"
# 	],
# 	"monthly": [
# 		"az_it.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "az_it.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "az_it.event.get_events"
# }
override_whitelisted_methods = {
    "erpnext.crm.doctype.lead.lead.make_opportunity": "az_it.az_it.python_scripts.overrides.lead.make_opportunity"
}
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "az_it.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["az_it.utils.before_request"]
# after_request = ["az_it.utils.after_request"]

# Job Events
# ----------
# before_job = ["az_it.utils.before_job"]
# after_job = ["az_it.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"az_it.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

fixtures = [
     {
        "doctype": "Client Script",
        "filters": [
            ["name", "in", [
                "Internal Customer Series" , 
                            ]]
        ]
    },
     {
        "doctype": "Server Script",
        "filters": [
            ["name", "in", [
                "Customer Internal Number Auto Assignment - Update" , 
                "Customer Internal Number Auto Assignment"
                            ]]
        ]
    }
     
      ]