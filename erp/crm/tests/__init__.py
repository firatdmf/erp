def works_in_a_book(user, name="Test Book"):
    """Assign `user` a book, and with it a directory to read customers from.

    A member assigned no book reads no directory, so a test that signs
    somebody in and expects them to see a company has to say where they
    work. Call it before making the records: one made outside a request
    is filed with the oldest book.
    """
    from accounting.models import Book

    book = Book.objects.filter(name=name).first() or Book.objects.create(name=name)
    user.member.books.add(book)
    return book
