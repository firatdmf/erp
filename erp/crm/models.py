from django.conf import settings
from django.db import models, transaction

# To store array field use this
from django.contrib.postgres.fields import ArrayField
from django.db.models import Q
from django.db.models.functions import Lower
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _


class DuplicateName(ValueError):
    """A second company, contact or supplier under a name CRM already has."""


class Directory(models.Model):
    """One list of customers and suppliers, kept apart from the others.

    Every company, contact and supplier is in exactly one directory, and
    every book reads exactly one (accounting.Book.directory). Books that
    are one business under two ledgers — a factory and its shop — point
    at the same directory and so share their customers; a branch that
    keeps its own customers has its own, and neither side sees the
    other's records, in a list, a search box or by typing an id.

    Sharing later is one change: point the branch's book at the other
    directory and move its records across.
    """

    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "Directories"

    def __str__(self):
        return self.name

    @classmethod
    def named_after(cls, name):
        """A new directory called `name`, or "name (2)" where that is taken.

        Never the existing one: handing a new book somebody else's
        directory because the names happen to match would share a
        customer list nobody asked to share.
        """
        base = (name or "").strip()[:90] or "Directory"
        candidate, n = base, 1
        while cls.objects.filter(name__iexact=candidate).exists():
            n += 1
            candidate = f"{base} ({n})"
        return cls.objects.create(name=candidate)


def visible_directory_ids():
    """The directories the person behind this request may read, or None
    where there is no wall to apply.

    None for work nobody is signed in for — a migration, a cron job, the
    shell, the storefront's API — and for a superuser, who is assigned
    every book implicitly (accounting.services_accounts.member_books).
    Everybody else reads the directories of the books they are assigned,
    which for a member assigned none is nothing at all.

    The user comes from the thread-local the order audit trail already
    keeps (operating.audit.CurrentUserMiddleware), and the answer is kept
    on that user object, which lives exactly as long as the request.
    """
    from operating.audit import get_current_user

    user = get_current_user()
    if user is None or user.is_superuser:
        return None
    ids = getattr(user, "_crm_directory_ids", None)
    if ids is None:
        from accounting.services_accounts import member_books

        member = getattr(user, "member", None)
        ids = frozenset(
            pk for pk in member_books(member).values_list("directory_id", flat=True)
            if pk is not None)
        user._crm_directory_ids = ids
    return ids


def working_directory():
    """The directory a new record lands in when nobody has said which.

    The acting member's working book decides, the same way it decides
    which book their orders land in. Outside a request the answer is the
    book get_default_book would give — CURRENT_ACCOUNT_BOOK_ID, else the
    oldest — and on an install with no book at all, the oldest directory.
    """
    from accounting.models import Book
    from accounting.services_accounts import acting_member, get_default_book

    member = acting_member()
    book = None
    if member is not None:
        book = get_default_book(member)
    else:
        pinned = str(getattr(settings, "CURRENT_ACCOUNT_BOOK_ID", "") or "").strip()
        if pinned.isdigit():
            book = Book.objects.filter(pk=int(pinned)).first()
        book = book or Book.objects.order_by("id").first()
    if book is not None and book.directory_id:
        return book.directory
    return Directory.objects.order_by("id").first() or Directory.objects.create(name="Main")


def reachable_from(model, directory_ids):
    """Q over `model` (a company, contact or supplier): the records
    someone reading `directory_ids` has — those at home in one of them,
    and those of another directory that have been shared with one.

    The shared half is a subquery on the link table rather than a join,
    so a record shared twice is still one row and the queryset can go on
    to be sliced, updated or deleted.
    """
    shared = (model.shared_with.through.objects
              .filter(directory_id__in=directory_ids)
              .values(f"{model._meta.model_name}_id"))
    return Q(directory_id__in=directory_ids) | Q(pk__in=shared)


class DirectoryManager(models.Manager):
    """The default manager of everything kept in a directory: it hands
    back only what the person behind the request may read.

    On the manager rather than in each view because these three models
    are read from over a hundred places in a dozen modules — lists,
    search boxes, the customer picker on every order and quote, a
    `get_object_or_404` behind each detail page — and a wall that each of
    them has to remember is a wall one of them will forget. Here a new
    query is walled without knowing it.

    A row reached THROUGH another record (`order.contact`) is not
    filtered — Django follows a foreign key with the base manager — so a
    page that may show an order can still name its customer.

    `everywhere` is the unwalled manager, for the few callers that must
    see across directories: the name check below, and data fixes.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        ids = visible_directory_ids()
        if ids is None:
            return qs
        return qs.filter(reachable_from(self.model, ids))

    def here(self):
        """The working book's customers: its directory's own records and
        those shared with it. What a list, a search box or a customer
        picker shows.

        Narrower than the wall for whoever reads several directories —
        the owner reads them all — and for them the wall is the wrong
        thing to list by: two businesses may each have their own "Ahmet",
        and a picker offering both cannot say which is which. So a list
        is one book's at a time, switched with the working book, while a
        page opened by id still opens anything its reader may read.

        Also the scope of "find the company called X, or make it", which
        must not hang a new contact on another business's company.
        """
        return self.get_queryset().filter(
            reachable_from(self.model, [working_directory().pk]))

    def of_book(self, book):
        """`here()` for a page that is about one book, whichever book its
        reader usually works in."""
        return self.get_queryset().filter(
            reachable_from(self.model, [book.directory_id]))


class OwnedRecordManager(models.Manager):
    """DirectoryManager for what hangs off a record — a note, a file.

    These carry no directory of their own; they are their owner's. So
    they are walled by it: an id typed into a note or download URL finds
    nothing unless the company, contact or supplier behind it is one the
    reader may open.
    """

    def get_queryset(self):
        qs = super().get_queryset()
        ids = visible_directory_ids()
        if ids is None:
            return qs
        return qs.filter(
            Q(contact__in=Contact.everywhere.filter(reachable_from(Contact, ids)))
            | Q(company__in=Company.everywhere.filter(reachable_from(Company, ids)))
            | Q(supplier__in=Supplier.everywhere.filter(reachable_from(Supplier, ids))))


def record_in_reach(*records):
    """Whether the reader may see every one of `records` (companies,
    contacts or suppliers; a None among them is nobody, and passes).

    For a single row already in hand — a label about to be printed —
    where `within_directories` is for a queryset.
    """
    ids = visible_directory_ids()
    if ids is None:
        return True
    for record in records:
        if record is None or record.directory_id in ids:
            continue
        if not record.shared_with.filter(pk__in=ids).exists():
            return False
    return True


def within_directories(queryset, *paths):
    """`queryset` without the rows that name somebody the reader may not
    see — for a model that POINTS AT a company, contact or supplier.

    Each of `paths` is a foreign key to one of them ("contact",
    "order__company"). A row passes where that key is empty or its
    record is in a directory the reader has; a task or an order about
    nobody in particular is nobody's secret.
    """
    ids = visible_directory_ids()
    if ids is None:
        return queryset
    for path in paths:
        record = queryset.model
        for step in path.split("__"):
            record = record._meta.get_field(step).related_model
        queryset = queryset.filter(
            Q(**{f"{path}__isnull": True})
            | Q(**{f"{path}__in": record.everywhere.filter(reachable_from(record, ids))}))
    return queryset


def of_books_in_reach(queryset, book_path="book"):
    """`queryset` without the rows of a book whose customer list the
    reader does not read — for what a SHARED customer's pages show.

    Sharing a customer shares who they are, not what each side does with
    them: once one is shared, their page opens for both businesses, and
    its orders, purchases and balances must still be each side's own.
    Two books on one directory go on seeing each other's, as before.

    `book_path` leads from a row to its book ("current_account__book"
    for an order); a row with no book passes.
    """
    ids = visible_directory_ids()
    if ids is None:
        return queryset
    return queryset.filter(
        Q(**{f"{book_path}__isnull": True})
        | Q(**{f"{book_path}__directory_id__in": ids}))


class LinkedRecordManager(models.Manager):
    """Default manager for a model that points at CRM records and shows
    their names wherever it is listed: a task, a purchase order.

    Its rows about another directory's customers are left out the way
    DirectoryManager leaves out the customers themselves.
    """

    def __init__(self, *paths):
        super().__init__()
        self.paths = paths

    def get_queryset(self):
        return within_directories(super().get_queryset(), *self.paths)


class UniqueNameMixin:
    """One record per name in a directory, whatever its case.

    Two records under one name cannot be told apart by anyone picking
    from a search box, so every later order, payment and statement lands
    on whichever was clicked. The rule is kept in three places, each for
    the callers the others miss: `clean()` tells a form which field is
    wrong, `save()` stops the views that build a record by hand, and the
    model's constraint stops whatever reaches the table without either.

    The name is unique within its directory, not across them: two
    businesses that share nothing may each have a customer called
    "Ahmet", and telling one that the name is taken would tell it who
    the other's customers are.

    A customer two businesses both deal with is ONE record, shared
    (`share_with`), not one in each directory — so a record shared into
    a directory counts as one of its names too, and cannot be shared
    into one that already has its own of that name. Those two are the
    same customer entered twice, to be merged rather than shown side by
    side.

    `unique_name_field` is the column checked; `unique_name_scope` narrows
    the records it is checked against (a supplier known by its contact's
    name is only compared with other such suppliers).
    """

    unique_name_field = "name"
    duplicate_name_message = _("A record with this name already exists.")

    def unique_name_scope(self, directory_id=None):
        # `everywhere`, then one directory's names — this record's own
        # unless told otherwise: the check has to mean the same thing
        # whoever is asking, and the walled manager would compare a
        # superuser's record against every directory.
        model = type(self)
        return model.everywhere.filter(
            reachable_from(model, [directory_id or self.directory_id]))

    def home_directory(self):
        """The directory a record with none yet belongs in."""
        return working_directory()

    def _settle_directory(self):
        if self.directory_id is None:
            self.directory = self.home_directory()

    def _name_is_taken(self, directory_id=None):
        field = self.unique_name_field
        value = (getattr(self, field) or "").strip()
        if not value:
            return False
        # Lower() on both sides, as the constraint does, so the check and
        # the table agree on what "the same name" is.
        taken = (self.unique_name_scope(directory_id)
                 .annotate(_n=Lower(field))
                 .filter(_n=Lower(models.Value(value))))
        if self.pk:
            taken = taken.exclude(pk=self.pk)
        return taken.exists()

    def clean_fields(self, exclude=None):
        # Settled before the fields are checked: a record validated
        # before its first save has no directory yet, and both the
        # "required" check and the name check below need one.
        self._settle_directory()
        super().clean_fields(exclude=exclude)

    def clean(self):
        super().clean()
        self._settle_directory()
        if self._name_is_taken():
            raise ValidationError({self.unique_name_field: self.duplicate_name_message})

    def save(self, *args, **kwargs):
        self._settle_directory()
        field = self.unique_name_field
        update_fields = kwargs.get("update_fields")
        if update_fields is None or field in update_fields:
            value = getattr(self, field)
            if isinstance(value, str):
                # "Woodline " beside "Woodline" is the same double.
                setattr(self, field, value.strip())
            if self._name_is_taken():
                raise DuplicateName(str(self.duplicate_name_message))
        adding = self._state.adding
        super().save(*args, **kwargs)
        if adding:
            self._shared_at_birth()

    def _shared_at_birth(self):
        """Hook: who a brand-new record is shared with."""

    def share_with(self, directory):
        """Let `directory`'s people work with this record as well.

        Refused where they already have one of this name: that is the
        same customer entered on both sides, and sharing would put the
        two side by side in every picker.
        """
        if directory.pk == self.directory_id:
            return
        if self._name_is_taken(directory.pk):
            raise DuplicateName(str(self.duplicate_name_message))
        self.shared_with.add(directory)

    def stop_sharing_with(self, directory):
        self.shared_with.remove(directory)


def shared_with_field(related_name):
    # Not editable for the reason `directory` is not: sharing goes
    # through share_with(), which checks for a twin first.
    return models.ManyToManyField(
        Directory, blank=True, related_name=related_name, editable=False)


def directory_field(related_name):
    # PROTECT: a directory goes only once it is empty. Not editable, so
    # no form offers it — a record is filed by where its author works,
    # and moved between directories as a deliberate data fix.
    return models.ForeignKey(
        Directory,
        on_delete=models.PROTECT,
        related_name=related_name,
        editable=False,
    )

# Create your models here.

# Type of client
# class ClientType(models.Model):
#     name = models.CharField(max_length=100, unique=True)
#     status = models.TextField( choices=[("prospect", "Prospect"), ("qualified", "Qualified")],max_length=200, blank=True, )

#     def __str__(self):
#         return self.name


# group: tech
class ClientGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(max_length=200, blank=True)

    def __str__(self):
        return self.name


class Company(UniqueNameMixin, models.Model):
    duplicate_name_message = _("A company with this name already exists.")

    # Who raised this record. Stamped automatically on first save by
    # erp.ownership.stamp_creator, from the request-scoped user. NULL on
    # rows that predate this column (and on anything created outside a
    # request); erp.ownership.can_edit treats those as admin-only.
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)ss",
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    directory = directory_field("companies")
    shared_with = shared_with_field("shared_companies")
    name = models.CharField(max_length=100, verbose_name="Company Name (required)")
    email = ArrayField(
        models.EmailField(max_length=254),
        blank=True,
        default=list,
        verbose_name="Email addresses"
    )
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
        verbose_name="Phone numbers"
    )
    website = models.CharField(max_length=100, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=50, blank=True)
    group = models.ForeignKey(
        ClientGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="companies",
    )
    status = models.CharField(
        choices=[("prospect", "Prospect"), ("qualified", "Qualified")],
        default=("prospect"),
    )

    objects = DirectoryManager()
    everywhere = models.Manager()

    # A company is shared with its people: the page of a company whose
    # contacts its reader cannot open is half a page.
    def share_with(self, directory):
        with transaction.atomic():
            super().share_with(directory)
            for contact in Contact.everywhere.filter(company=self):
                contact.share_with(directory)

    def stop_sharing_with(self, directory):
        with transaction.atomic():
            super().stop_sharing_with(directory)
            for contact in Contact.everywhere.filter(company=self):
                contact.stop_sharing_with(directory)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Companies"
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "directory", name="uniq_company_name_ci",
                violation_error_message=_("A company with this name already exists.")),
        ]


class Contact(UniqueNameMixin, models.Model):
    duplicate_name_message = _("A contact with this name already exists.")

    # Who raised this record. Stamped automatically on first save by
    # erp.ownership.stamp_creator, from the request-scoped user. NULL on
    # rows that predate this column (and on anything created outside a
    # request); erp.ownership.can_edit treats those as admin-only.
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)ss",
        editable=False,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    directory = directory_field("contacts")
    shared_with = shared_with_field("shared_contacts")
    name = models.CharField(max_length=50, verbose_name="Contact Name (required)")
    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="contacts",
    )
    job_title = models.CharField(max_length=25, blank=True, verbose_name="Job Title")
    email = ArrayField(
        models.EmailField(max_length=254),
        blank=True,
        default=list,
        verbose_name="Email addresses"
    )
    backgroundInfo = models.TextField(
        max_length=200,
        verbose_name="Background info",
        blank=True,
    )
    phone = ArrayField(
        models.CharField(max_length=20),
        blank=True,
        default=list,
        verbose_name="Phone numbers"
    )
    address = models.TextField(max_length=255, blank=True)
    country = models.CharField(max_length=50, blank=True)
    birthday = models.DateField(null=True, blank=True)
    group = models.ForeignKey(
        ClientGroup,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="contacts",
    )

    objects = DirectoryManager()
    everywhere = models.Manager()

    def home_directory(self):
        # A contact is filed with its company: one of them in each of two
        # directories would be a company page listing people half its
        # readers cannot open.
        if self.company_id:
            return self.company.directory
        return working_directory()

    def _shared_at_birth(self):
        # ...and shared with whoever its company is shared with.
        if self.company_id:
            self.shared_with.set(self.company.shared_with.all())

    def __str__(self):
        if self.company:
            return f"{self.name} | {self.company.name}"
        else:
            return self.name

    class Meta:
        verbose_name_plural = "Contacts"
        constraints = [
            models.UniqueConstraint(
                Lower("name"), "directory", name="uniq_contact_name_ci",
                violation_error_message=_("A contact with this name already exists.")),
        ]


class Supplier(UniqueNameMixin, models.Model):
    duplicate_name_message = _("A supplier with this name already exists.")

    # Who raised this record — the same column, stamp and reading as on
    # Contact above (erp.ownership). NULL on rows older than the column.
    created_by = models.ForeignKey(
        "auth.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="created_%(class)ss",
        editable=False,
    )

    # A supplier goes by its company name, or by its contact's when it has
    # none (see __str__) — and that name is unique among suppliers.
    directory = directory_field("suppliers")
    shared_with = shared_with_field("shared_suppliers")
    company_name = models.CharField(max_length=300, null=True, blank=True)
    contact_name = models.CharField(max_length=300, null=True, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    website = models.CharField(max_length=200, blank=True)
    address = models.CharField(max_length=255, blank=True)
    country = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Optional links to existing CRM contact / company records so a
    # supplier can be associated with the same person/org you already
    # track elsewhere. Both blank — supplier may stand alone.
    linked_contact = models.ForeignKey(
        "Contact",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_suppliers",
    )
    linked_company = models.ForeignKey(
        "Company",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="linked_suppliers",
    )

    objects = DirectoryManager()
    everywhere = models.Manager()

    @property
    def unique_name_field(self):
        return "company_name" if (self.company_name or "").strip() else "contact_name"

    def unique_name_scope(self, directory_id=None):
        # A contact's name is only the supplier's name where there is no
        # company name: two companies may both be reached through "Ahmet".
        mine = super().unique_name_scope(directory_id)
        if self.unique_name_field == "contact_name":
            return mine.filter(Q(company_name__isnull=True) | Q(company_name=""))
        return mine

    def clean(self):
        # Ensure that you call super().clean() to maintain the default validation behavior.
        super().clean()
        if not self.company_name and not self.contact_name:
            raise ValidationError(
                "You have to enter either, company name or contact name."
            )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("company_name"), "directory", name="uniq_supplier_company_name_ci",
                condition=Q(company_name__gt=""),
                violation_error_message=_("A supplier with this name already exists.")),
            models.UniqueConstraint(
                Lower("contact_name"), "directory", name="uniq_supplier_contact_name_ci",
                condition=(Q(company_name__isnull=True) | Q(company_name=""))
                          & Q(contact_name__gt=""),
                violation_error_message=_("A supplier with this name already exists.")),
        ]

    def __str__(self):
        if self.company_name:
            return self.company_name
        elif self.contact_name:
            return self.contact_name
        return "Unnamed Supplier"


class Note(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    modified_date = models.DateTimeField(auto_now=True)
    # If I delete the contact, then delete the notes associated to it.
    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True, related_name="notes"
    )
    content = models.TextField()

    objects = OwnedRecordManager()
    everywhere = models.Manager()

    # below is for admin view
    def __str__(self):
        if self.contact:
            return f"Note for {self.contact}"
        elif self.company:
            return f"Note for {self.company}"
        elif self.supplier:
            return f"Note for {self.supplier}"
        else:
            return "Unassociated Note"


class CompanyFollowUp(models.Model):
    """
    Tracks automated follow-up emails sent to prospect companies.
    Follow-up schedule:
    - Email 1: Sent immediately when company is created
    - Email 2: 3 days after email 1
    - Email 3: 7 days after email 2 (10 days total)
    - Email 4: 14 days after email 3 (24 days total)
    - Email 5: 30 days after email 4 (54 days total)
    """
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        related_name="followup",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_email_sent_at = models.DateTimeField(null=True, blank=True)
    emails_sent_count = models.IntegerField(default=0)
    stopped_reason = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Reason why follow-ups were stopped (e.g., 'status_changed', 'max_emails_reached', 'reply_received')"
    )
    stopped_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name_plural = "Company Follow Ups"

    def __str__(self):
        return f"Follow-up for {self.company.name} - {self.emails_sent_count}/5 emails sent"

    def should_send_email(self):
        """
        Determines if a follow-up email should be sent based on schedule.
        Returns: (should_send: bool, days_to_wait: int)
        
        Note: Email 1 is sent immediately via signal, so this handles emails 2-5.
        """
        if not self.is_active or self.emails_sent_count >= 5:
            return False, 0

        # Email 1 is already sent immediately via signal
        # This handles emails 2-5 with schedule: [3, 7, 14, 30] days after previous email
        schedule = [3, 7, 14, 30]  # Days to wait after each email
        
        from django.utils import timezone
        now = timezone.now()
        
        # Emails 2-5: wait specified days after last email
        if self.emails_sent_count == 0:
            # Edge case: Email 1 wasn't sent for some reason, shouldn't happen
            return False, 0
        
        # Calculate which email we're about to send (2-5)
        next_email_index = self.emails_sent_count  # Since email 1 is already sent
        
        if next_email_index > len(schedule):
            return False, 0
        
        reference_date = self.last_email_sent_at
        days_to_wait = schedule[next_email_index - 1]  # -1 because email 1 is index 0
        
        days_elapsed = (now - reference_date).days
        return days_elapsed >= days_to_wait, days_to_wait

    def mark_email_sent(self):
        """Mark that an email was sent and increment counter."""
        from django.utils import timezone
        self.emails_sent_count += 1
        self.last_email_sent_at = timezone.now()
        
        if self.emails_sent_count >= 5:
            self.is_active = False
            self.stopped_reason = "max_emails_reached"
            self.stopped_at = timezone.now()
        
        self.save()

    def stop_followups(self, reason):
        """Stop follow-up emails for this company."""
        from django.utils import timezone
        self.is_active = False
        self.stopped_reason = reason
        self.stopped_at = timezone.now()
        self.save()


# Extensions that execute rather than describe. A CRM should carry
# whatever paperwork a customer sends, so the rule is open-minus-the-
# dangerous-ones rather than a whitelist: these are the endings that turn
# the file list into a way to hand a colleague a program, and nothing a
# salesperson legitimately attaches ends in one. A zipped executable
# still gets through — that is the accepted cost of accepting archives.
BLOCKED_ATTACHMENT_EXTENSIONS = frozenset({
    # Windows executables and installers
    "exe", "msi", "com", "scr", "pif", "cpl", "msc", "lnk", "reg",
    # Shell and script interpreters
    "bat", "cmd", "sh", "bash", "ps1", "psm1", "vbs", "vbe",
    "js", "jse", "wsf", "wsh", "hta",
    # Packaged applications
    "jar", "apk", "app", "deb", "rpm",
    # Macro-enabled Office documents — the classic mail-borne payload
    "docm", "dotm", "xlsm", "xltm", "xlam", "pptm", "potm", "ppam",
})


def validate_attachment_type(file):
    """Refuse the file endings that run instead of open.

    Only the LAST extension is examined, which is the point:
    "invoice.pdf.exe" is an executable wearing a document's name, and
    that is exactly the shape this is here to stop.
    """
    name = getattr(file, "name", "") or ""
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    if ext in BLOCKED_ATTACHMENT_EXTENSIONS:
        raise ValidationError(
            f".{ext} files cannot be attached — programs and scripts are "
            f"not accepted. Put it in a zip if it really has to travel.")
    return file


def content_type_for(filename, declared=""):
    """Work out a file's type from its name, not from what the client said.

    The browser supplies `content_type` on an upload and a crafted client
    can supply anything, so trusting it lets a caller choose how their
    file is later served — declare a payload "image/svg+xml" and it comes
    back inline, on our own origin. The extension is not proof of content
    either, but it is at least ours to reason about, and the download view
    only ever renders a short list of types inline.
    """
    import mimetypes

    guess, _ = mimetypes.guess_type(filename or "")
    return (guess or declared or "application/octet-stream")[:120]


def validate_attachment_size(file):
    """Cap an attachment at 25 MB.

    Larger than the 10 MB product-image limit because these are the
    documents a salesperson hangs off a client — a signed contract scan
    or a spec sheet routinely runs past ten.
    """
    size_threshold = 26214400  # 25 MB
    if file.size > size_threshold:
        raise ValidationError("The maximum file size that can be uploaded is 25MB")
    return file


class Attachment(models.Model):
    """A file hung off a CRM record — contact, company or supplier.

    The bytes live in the Bunny Storage Zone and the row keeps only the
    storage `path` — never a CDN URL. Readers go through the
    login-required download view, which fetches from the Storage API
    with the account key, so an attachment has no public address to
    leak or guess.

    There is no local fallback for a failed upload. MEDIA_ROOT is a
    container path with no volume mounted: a file written there looks
    saved and is gone on the next deploy, which is how 3,611 warehouse
    rolls ended up pointing at photos that no longer exist. A refused
    upload the user can retry beats a file that quietly disappears.
    `file` is only for a dev box running without Bunny configured, where
    the local disk is the intent rather than a consolation prize.
    """

    contact = models.ForeignKey(
        Contact, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, blank=True, null=True,
        related_name="attachments",
    )
    name = models.CharField(max_length=255)
    path = models.CharField(
        max_length=700, blank=True,
        help_text="Path inside the Bunny Storage Zone",
    )
    file = models.FileField(
        upload_to="crm/attachments/%Y/%m/", blank=True, null=True,
        validators=[validate_attachment_size, validate_attachment_type],
    )
    size = models.PositiveIntegerField(default=0, help_text="Bytes")
    content_type = models.CharField(max_length=120, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        blank=True, null=True, related_name="crm_attachments",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    objects = OwnedRecordManager()
    everywhere = models.Manager()

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self):
        return self.name

    @property
    def href(self):
        """Every reader goes through the login-required download view."""
        from django.urls import reverse
        return reverse("crm:download_attachment", args=[self.pk])

    @property
    def extension(self):
        return (self.name.rsplit(".", 1)[-1].upper() if "." in self.name else "")

    @property
    def is_image(self):
        return self.content_type.startswith("image/")

    def pretty_size(self):
        n = self.size or 0
        for unit in ("B", "KB", "MB", "GB"):
            if n < 1024 or unit == "GB":
                return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024.0
