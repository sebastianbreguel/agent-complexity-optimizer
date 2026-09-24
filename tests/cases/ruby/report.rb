class Report
  def match(users, orders)
    users.each do |u|
      orders.each do |o| # expect: nested-loop
        puts o if o.user_id == u.id
      end
    end
  end

  def walk(orders)
    orders.each do |order|
      order.lines.each { |line| puts line }
    end
  end

  def selected(items, ids)
    items.select { |i| ids.include?(i.id) } # expect: membership-in-loop
  end

  def load(ids)
    ids.each do |id|
      User.find_by(id: id) # expect: io-or-query-in-loop
    end
  end

  def by_id(items)
    items.inject({}) { |h, item| h.merge(item.id => item) } # expect: quadratic-accumulation
  end

  def by_id_fast(items)
    items.each_with_object({}) { |item, h| h[item.id] = item }
  end

  def preload(ids)
    User.where(id: ids).to_a
  end
end
